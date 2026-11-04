import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_register_success():
    email = f"test_{pytest.importorskip('time').time()}@example.com"
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": "Nguyễn Văn Test",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["role"] == "user"
    assert data["credits"] >= 5000


def test_register_duplicate_email():
    email = "duplicate@example.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123!"},
    )
    # Thử đăng ký lần 2 với cùng email
    res2 = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123!"},
    )
    assert res2.status_code == 400
    assert "đã được sử dụng" in res2.json().get("detail", "")


def test_login_and_me_flow():
    email = "flow_test@example.com"
    password = "MySecurePassword123"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test Flow"},
    )

    # 1. Login sai mật khẩu -> 401
    bad_login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "wrongpassword"},
    )
    assert bad_login.status_code == 401

    # 2. Login đúng -> 200 + access_token + cookie
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"
    assert "refresh_token" in login_res.cookies
    token = login_data["access_token"]

    # 3. /api/auth/me với token -> 200
    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # 4. /api/auth/me không có token -> 401
    no_auth = client.get("/api/auth/me")
    assert no_auth.status_code == 401

    # 5. Refresh token
    refresh_res = client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": login_res.cookies["refresh_token"]},
    )
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.json()

    # 6. Logout
    logout_res = client.post(
        "/api/auth/logout",
        cookies={"refresh_token": login_res.cookies["refresh_token"]},
    )
    assert logout_res.status_code == 200


def test_forgot_password_flow():
    email = "forgot_test@example.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "OldPassword123"},
    )

    # Request forgot password
    forgot_res = client.post(
        "/api/auth/forgot-password",
        json={"email": email},
    )
    assert forgot_res.status_code == 200
    assert "hướng dẫn" in forgot_res.json().get("message", "").lower()

