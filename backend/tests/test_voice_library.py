"""Tests cho Voice Library tập trung (Issue #18)."""
from __future__ import annotations

import time
from typing import Dict, Tuple

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.db import AsyncSessionLocal
from app.main import app
from app.models.user import User
from app.models.voice import Voice, VoiceFavorite
from app.services.voice_library_service import VoiceLibraryService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_voice(
    *,
    provider: str = "edge",
    provider_voice_id: str = "vi-VN-NamMinhNeural",
    name: str = "Nam Minh",
    language: str = "vi-VN",
    gender: str = "Male",
    voice_type: str = "system",
    is_active: bool = True,
    owner_id: int | None = None,
    tier: str = "free",
    credit_multiplier: float = 1.0,
    tags: str | None = None,
) -> Voice:
    return Voice(
        owner_id=owner_id,
        name=name,
        display_name=name,
        provider=provider,
        provider_voice_id=provider_voice_id,
        voice_type=voice_type,
        language=language,
        gender=gender,
        tags=tags,
        visibility="public" if owner_id is None else "private",
        status="ready",
        is_active=is_active,
        tier=tier,
        credit_multiplier=credit_multiplier,
        total_uses=0,
    )


async def _get_auth_headers(is_admin: bool = False) -> Tuple[Dict[str, str], int]:
    email = f"user_{'admin_' if is_admin else ''}{time.time_ns()}@test.com"
    password = "Password123!"
    async with AsyncSessionLocal() as db:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name="Test User",
            role="admin" if is_admin else "user",
            is_active=True,
            is_admin=is_admin,
            is_verified=True,
            credit_balance=10000,
            credits=10000,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = user.id

    token = create_access_token(data={"sub": str(user_id), "email": email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}, user_id


# ---------------------------------------------------------------------------
# VoiceLibraryService Unit Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_creates_new_voices() -> None:
    provider_voices = [
        {"id": f"vi-VN-NamMinhNeural-{time.time_ns()}", "name": "Nam Minh", "locale": "vi-VN", "gender": "Male"},
        {"id": f"vi-VN-HoaiMyNeural-{time.time_ns()}", "name": "Hoài My", "locale": "vi-VN", "gender": "Female"},
    ]
    async with AsyncSessionLocal() as db:
        synced = await VoiceLibraryService.sync_system_voices(db, provider_voices, provider="edge")
        assert synced == 2


@pytest.mark.asyncio
async def test_sync_updates_existing_voices() -> None:
    pvid = f"test-sync-update-{time.time_ns()}"
    provider_voices_v1 = [{"id": pvid, "name": "Old Name", "locale": "en-US", "gender": "Male"}]
    provider_voices_v2 = [{"id": pvid, "name": "Updated Name", "locale": "en-US", "gender": "Male"}]

    async with AsyncSessionLocal() as db:
        await VoiceLibraryService.sync_system_voices(db, provider_voices_v1, provider="edge")
        await VoiceLibraryService.sync_system_voices(db, provider_voices_v2, provider="edge")
        voice = await VoiceLibraryService.get_voice_by_provider_id(db, "edge", pvid)
        assert voice is not None
        assert voice.name == "Updated Name"


@pytest.mark.asyncio
async def test_sync_skips_voices_without_id() -> None:
    provider_voices = [{"name": "No ID Voice", "locale": "vi-VN", "gender": "Female"}]
    async with AsyncSessionLocal() as db:
        synced = await VoiceLibraryService.sync_system_voices(db, provider_voices)
        assert synced == 0


@pytest.mark.asyncio
async def test_toggle_favorite_adds_then_removes() -> None:
    async with AsyncSessionLocal() as db:
        user = User(
            email=f"vl_test_{time.time_ns()}@test.com",
            hashed_password=hash_password("TestPass123!"),
            full_name="VL Test",
            is_active=True,
            is_verified=True,
            credit_balance=1000,
            credits=1000,
        )
        db.add(user)
        await db.flush()

        voice = _make_voice(
            provider_voice_id=f"test-fav-{time.time_ns()}",
            name=f"Test Voice {time.time_ns()}",
        )
        db.add(voice)
        await db.commit()
        await db.refresh(user)
        await db.refresh(voice)
        user_id, voice_id = user.id, voice.id

    async with AsyncSessionLocal() as db:
        is_fav = await VoiceLibraryService.toggle_favorite(db, user_id, voice_id)
        assert is_fav is True

        fav_ids = await VoiceLibraryService.get_favorites(db, user_id)
        assert voice_id in fav_ids

    async with AsyncSessionLocal() as db:
        is_fav = await VoiceLibraryService.toggle_favorite(db, user_id, voice_id)
        assert is_fav is False

        fav_ids = await VoiceLibraryService.get_favorites(db, user_id)
        assert voice_id not in fav_ids


@pytest.mark.asyncio
async def test_get_favorites_empty() -> None:
    async with AsyncSessionLocal() as db:
        user = User(
            email=f"vl_empty_{time.time_ns()}@test.com",
            hashed_password=hash_password("TestPass123!"),
            full_name="Empty Fav User",
            is_active=True,
            is_verified=True,
            credit_balance=0,
            credits=0,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = user.id

    async with AsyncSessionLocal() as db:
        fav_ids = await VoiceLibraryService.get_favorites(db, user_id)
        assert fav_ids == []


@pytest.mark.asyncio
async def test_list_voices_returns_active_only() -> None:
    pvid_active = f"active-{time.time_ns()}"
    pvid_inactive = f"inactive-{time.time_ns()}"

    async with AsyncSessionLocal() as db:
        db.add(_make_voice(provider_voice_id=pvid_active, name="Active Voice", is_active=True))
        db.add(_make_voice(provider_voice_id=pvid_inactive, name="Inactive Voice", is_active=False))
        await db.commit()

    async with AsyncSessionLocal() as db:
        result = await VoiceLibraryService.list_voices(db, user_id=None, only_active=True)
        active_ids = {v.provider_voice_id for v in result["voices"]}
        assert pvid_active in active_ids
        assert pvid_inactive not in active_ids


@pytest.mark.asyncio
async def test_list_voices_filter_by_language() -> None:
    pvid_vi = f"vi-filter-{time.time_ns()}"
    pvid_en = f"en-filter-{time.time_ns()}"

    async with AsyncSessionLocal() as db:
        db.add(_make_voice(provider_voice_id=pvid_vi, name="VI Voice", language="vi-VN"))
        db.add(_make_voice(provider_voice_id=pvid_en, name="EN Voice", language="en-US"))
        await db.commit()

    async with AsyncSessionLocal() as db:
        result = await VoiceLibraryService.list_voices(db, user_id=None, language="vi-VN")
        lang_values = {v.language for v in result["voices"]}
        assert "vi-VN" in lang_values
        en_voices = [v for v in result["voices"] if v.provider_voice_id == pvid_en]
        assert len(en_voices) == 0


@pytest.mark.asyncio
async def test_list_voices_search_by_name() -> None:
    unique_name = f"UniqueSuperVoice{time.time_ns()}"
    pvid = f"search-test-{time.time_ns()}"

    async with AsyncSessionLocal() as db:
        db.add(_make_voice(provider_voice_id=pvid, name=unique_name))
        await db.commit()

    async with AsyncSessionLocal() as db:
        result = await VoiceLibraryService.list_voices(db, user_id=None, search=unique_name[:10])
        matched = [v for v in result["voices"] if v.provider_voice_id == pvid]
        assert len(matched) == 1


@pytest.mark.asyncio
async def test_list_voices_favorites_only() -> None:
    pvid_fav = f"fav-only-{time.time_ns()}"
    pvid_other = f"other-{time.time_ns()}"

    async with AsyncSessionLocal() as db:
        user = User(
            email=f"vl_fav_{time.time_ns()}@test.com",
            hashed_password=hash_password("TestPass123!"),
            full_name="Fav Only User",
            is_active=True,
            is_verified=True,
            credit_balance=0,
            credits=0,
        )
        db.add(user)
        v1 = _make_voice(provider_voice_id=pvid_fav, name="Fav Voice")
        v2 = _make_voice(provider_voice_id=pvid_other, name="Other Voice")
        db.add(v1)
        db.add(v2)
        await db.flush()
        fav = VoiceFavorite(user_id=user.id, voice_id=v1.id)
        db.add(fav)
        await db.commit()
        user_id = user.id

    async with AsyncSessionLocal() as db:
        result = await VoiceLibraryService.list_voices(
            db, user_id=user_id, favorites_only=True
        )
        ids = {v.provider_voice_id for v in result["voices"]}
        assert pvid_fav in ids
        assert pvid_other not in ids


@pytest.mark.asyncio
async def test_set_voice_active_false() -> None:
    pvid = f"admin-toggle-{time.time_ns()}"
    async with AsyncSessionLocal() as db:
        v = _make_voice(provider_voice_id=pvid, name="Admin Toggle Voice", is_active=True)
        db.add(v)
        await db.commit()
        await db.refresh(v)
        voice_id = v.id

    async with AsyncSessionLocal() as db:
        updated = await VoiceLibraryService.set_voice_active(db, voice_id, False)
        assert updated is not None
        assert updated.is_active is False


@pytest.mark.asyncio
async def test_set_voice_active_nonexistent() -> None:
    async with AsyncSessionLocal() as db:
        result = await VoiceLibraryService.set_voice_active(db, 999999, False)
        assert result is None


@pytest.mark.asyncio
async def test_remove_user_cloned_voices() -> None:
    cloned_ref = f"clone_remove_{time.time_ns()}"
    async with AsyncSessionLocal() as db:
        v = Voice(
            name="Clone to Remove",
            display_name="Clone to Remove",
            provider="user_clone",
            provider_voice_id=cloned_ref,
            voice_type="cloned",
            language="vi-VN",
            gender="Female",
            visibility="private",
            status="ready",
            is_active=True,
            tier="free",
            credit_multiplier=1.0,
            total_uses=0,
            cloned_voice_ref=cloned_ref,
        )
        db.add(v)
        await db.commit()

    async with AsyncSessionLocal() as db:
        await VoiceLibraryService.remove_user_cloned_voices(db, cloned_ref)
        voice = await VoiceLibraryService.get_voice_by_provider_id(db, "user_clone", cloned_ref)
        assert voice is None


@pytest.mark.asyncio
async def test_increment_voice_usage() -> None:
    pvid = f"usage-{time.time_ns()}"
    async with AsyncSessionLocal() as db:
        v = _make_voice(provider_voice_id=pvid, name="Usage Counter Voice")
        db.add(v)
        await db.commit()

    async with AsyncSessionLocal() as db:
        await VoiceLibraryService.increment_voice_usage(db, pvid)
        voice = await VoiceLibraryService.get_voice_by_provider_id(db, "edge", pvid)
        assert voice is not None
        assert voice.total_uses == 1


# ---------------------------------------------------------------------------
# API Endpoint Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_library_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/voices/library")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_library_returns_list() -> None:
    pvid = f"lib-item-{time.time_ns()}"
    async with AsyncSessionLocal() as db:
        v = _make_voice(provider_voice_id=pvid, name="Lib Item Test", tags="tin tức")
        db.add(v)
        await db.commit()

    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/voices/library", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "voices" in data
        assert "total" in data
        assert "favorite_ids" in data
        assert data["total"] > 0


@pytest.mark.asyncio
async def test_get_library_tab_mine() -> None:
    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/voices/library?tab=mine", headers=headers)
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_library_tab_favorites() -> None:
    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/voices/library?tab=favorites", headers=headers)
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_toggle_favorite_nonexistent_voice() -> None:
    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/voices/library/999999/favorite", headers=headers)
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_toggle_favorite_existing_voice() -> None:
    pvid = f"api-fav-{time.time_ns()}"
    async with AsyncSessionLocal() as db:
        v = _make_voice(provider_voice_id=pvid, name="API Fav Voice")
        db.add(v)
        await db.commit()
        await db.refresh(v)
        voice_id = v.id

    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/voices/library/{voice_id}/favorite", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["voice_id"] == voice_id
        assert data["is_favorite"] is True

        # Toggle off
        resp2 = await client.post(f"/api/voices/library/{voice_id}/favorite", headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["is_favorite"] is False


@pytest.mark.asyncio
async def test_get_favorite_ids() -> None:
    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/voices/favorites", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_sync_voices_requires_admin() -> None:
    headers, _ = await _get_auth_headers(is_admin=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/voices/library/sync", headers=headers)
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sync_voices_as_admin() -> None:
    headers, _ = await _get_auth_headers(is_admin=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/voices/library/sync", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "synced" in data


@pytest.mark.asyncio
async def test_update_voice_requires_admin() -> None:
    headers, _ = await _get_auth_headers(is_admin=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            "/api/voices/library/1",
            headers=headers,
            json={"is_active": False},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_voice_as_admin() -> None:
    pvid = f"admin-update-{time.time_ns()}"
    async with AsyncSessionLocal() as db:
        v = _make_voice(provider_voice_id=pvid, name="Admin Update Voice")
        db.add(v)
        await db.commit()
        await db.refresh(v)
        voice_id = v.id

    headers, _ = await _get_auth_headers(is_admin=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            f"/api/voices/library/{voice_id}",
            headers=headers,
            json={"display_name": "Updated Display Name", "tier": "premium", "credit_multiplier": 2.0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "Updated Display Name"
        assert data["tier"] == "premium"
        assert data["credit_multiplier"] == 2.0


@pytest.mark.asyncio
async def test_update_nonexistent_voice() -> None:
    headers, _ = await _get_auth_headers(is_admin=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            "/api/voices/library/999999",
            headers=headers,
            json={"is_active": False},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_library_filter_language() -> None:
    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/voices/library?language=vi-VN", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        for v in data["voices"]:
            assert v["language"] == "vi-VN"


@pytest.mark.asyncio
async def test_library_filter_gender() -> None:
    pvid = f"gender-filter-{time.time_ns()}"
    async with AsyncSessionLocal() as db:
        db.add(_make_voice(provider_voice_id=pvid, name="Gender Test Female", gender="Female", language="vi-VN"))
        await db.commit()

    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/voices/library?gender=Female", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        for v in data["voices"]:
            assert v["gender"] == "Female"


@pytest.mark.asyncio
async def test_sync_cloned_voice_to_library_lifecycle() -> None:
    from app.models.cloned_voice import ClonedVoice

    cid = f"test_clone_{time.time_ns()}"
    cloned = ClonedVoice(
        voice_id=cid,
        user_id=1,
        name="Cloned Test Voice",
        description="A great cloned voice",
        audio_sample_path="/tmp/sample.mp3",
        sample_duration=12.5,
        sample_size_bytes=50000,
        quality_score=4.8,
        gender="Male",
        language="vi-VN",
        provider="local",
        status="ready",
        is_active=True,
        preview_audio_url=f"/api/voices/cloned/{cid}/preview",
    )

    async with AsyncSessionLocal() as db:
        v = await VoiceLibraryService.sync_cloned_voice_to_library(db, cloned)
        assert v is not None
        assert v.cloned_voice_ref == cid
        assert v.voice_type == "cloned"
        assert v.name == "Cloned Test Voice"

    # Update cloned voice
    cloned.name = "Updated Cloned Voice"
    cloned.description = "Updated description"
    async with AsyncSessionLocal() as db:
        v_updated = await VoiceLibraryService.sync_cloned_voice_to_library(db, cloned)
        assert v_updated.name == "Updated Cloned Voice"
        assert v_updated.description == "Updated description"


@pytest.mark.asyncio
async def test_update_voice_with_all_fields_as_admin() -> None:
    pvid = f"admin-full-update-{time.time_ns()}"
    async with AsyncSessionLocal() as db:
        v = _make_voice(provider_voice_id=pvid, name="Admin Full Update Voice")
        db.add(v)
        await db.commit()
        await db.refresh(v)
        voice_id = v.id

    headers, _ = await _get_auth_headers(is_admin=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            f"/api/voices/library/{voice_id}",
            headers=headers,
            json={
                "is_active": False,
                "tier": "premium",
                "credit_multiplier": 2.5,
                "tags": "tin tức,quảng cáo",
                "display_name": "New Display Name",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is False
        assert data["tier"] == "premium"
        assert data["credit_multiplier"] == 2.5
        assert data["tags"] == "tin tức,quảng cáo"
        assert data["display_name"] == "New Display Name"


@pytest.mark.asyncio
async def test_library_filter_voice_type() -> None:
    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/voices/library?voice_type=system", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        for v in data["voices"]:
            assert v["voice_type"] == "system"


@pytest.mark.asyncio
async def test_library_service_extra_edge_cases() -> None:
    async with AsyncSessionLocal() as db:
        # Non-existent provider voice
        v = await VoiceLibraryService.get_voice_by_provider_id(db, "unknown", "nonexistent")
        assert v is None

        # Increment usage on non-existent voice should not crash
        await VoiceLibraryService.increment_voice_usage(db, "nonexistent-pvid")

        # list_voices with vi filter
        res = await VoiceLibraryService.list_voices(db, language="vi")
        assert "voices" in res

        # list_voices with owner_only
        res_owner = await VoiceLibraryService.list_voices(db, user_id=1, owner_only=True)
        assert "voices" in res_owner

