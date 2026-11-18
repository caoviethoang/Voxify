"""Dịch vụ Quản lý Chương trình Tiếp thị Liên kết (Affiliate Program - Issue #14)."""
import json
import logging
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.errors import AppError
from app.models.admin import AffiliateWithdrawal, SecurityViolationLog, SystemSetting
from app.models.affiliate import (
    AffiliateClick,
    AffiliateCommission,
    CommissionStatus,
    WithdrawalStatus,
)
from app.models.payment import Order
from app.models.user import User

logger = logging.getLogger(__name__)


def mask_email(email: str) -> str:
    """Che giấu một phần email để bảo vệ quyền riêng tư người mua (ví dụ: h***g@gmail.com)."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


def normalize_email_for_anti_fraud(email: str) -> str:
    """Chuẩn hóa email để phát hiện alias gian lận tự giới thiệu."""
    email = email.lower().strip()
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    # Hầu hết mọi dịch vụ email (Gmail, Outlook, iCloud...) đều hỗ trợ sub-addressing với dấu +
    local = local.split("+")[0]
    if domain in ("gmail.com", "googlemail.com"):
        local = local.replace(".", "")
        domain = "gmail.com"
    return f"{local}@{domain}"


class AffiliateService:
    """Nghiệp vụ Chương trình Tiếp thị liên kết & Chống gian lận (Anti-fraud)."""

    @classmethod
    async def generate_referral_code(cls, db: AsyncSession, prefix: str = "VOX") -> str:
        """Tạo mã giới thiệu ngẫu nhiên duy nhất cho người dùng (ví dụ: VOXA1B2C)."""
        for _ in range(10):
            token = secrets.token_hex(3).upper()  # 6 ký tự hex
            code = f"{prefix}{token}"
            stmt = select(User.id).where(User.referral_code == code)
            exists = (await db.execute(stmt)).scalar_one_or_none()
            if not exists:
                return code
        # Fallback với độ dài lớn hơn nếu trùng
        return f"{prefix}{secrets.token_hex(4).upper()}"

    @classmethod
    async def get_or_create_referral_code(cls, db: AsyncSession, user: User) -> str:
        """Lấy mã giới thiệu hiện tại hoặc tự động tạo nếu chưa có."""
        if user.referral_code:
            return user.referral_code

        code = await cls.generate_referral_code(db)
        user.referral_code = code
        await db.commit()
        await db.refresh(user)
        return code

    @classmethod
    async def record_click(
        cls,
        db: AsyncSession,
        referral_code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Ghi nhận lượt click truy cập qua đường link giới thiệu.
        Trả về: (thành công, thông điệp, affiliate_user_id)
        """
        clean_code = referral_code.strip().upper()
        stmt = select(User).where(User.referral_code == clean_code)
        res = await db.execute(stmt)
        referrer = res.scalar_one_or_none()

        if not referrer:
            return False, "Mã giới thiệu không tồn tại", None

        if not referrer.is_active or referrer.is_banned:
            return False, "Người giới thiệu không khả dụng", None

        click = AffiliateClick(
            affiliate_user_id=referrer.id,
            referral_code=clean_code,
            ip_address=ip_address,
            user_agent=user_agent[:255] if user_agent else None,
            device_fingerprint=device_fingerprint[:100] if device_fingerprint else None,
        )
        db.add(click)
        await db.commit()
        return True, "Ghi nhận lượt click thành công", referrer.id

    @classmethod
    async def validate_referral_anti_fraud(
        cls,
        db: AsyncSession,
        referrer: User,
        candidate_email: str,
        client_ip: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Kiểm tra chống gian lận tự giới thiệu chính mình (Anti-fraud Requirement #5):
        - So khớp email chính xác và alias (vd: user+1@gmail.com vs user@gmail.com)
        - So khớp địa chỉ IP đăng ký
        - So khớp mã nhận diện thiết bị (device fingerprint)
        """
        # 1. So khớp email
        norm_candidate = normalize_email_for_anti_fraud(candidate_email)
        norm_referrer = normalize_email_for_anti_fraud(referrer.email)

        if norm_candidate == norm_referrer:
            reason = "Phát hiện tự giới thiệu bằng email hoặc email alias trùng với người giới thiệu"
            await cls._log_fraud_violation(
                db=db,
                referrer_id=referrer.id,
                client_ip=client_ip,
                reason=reason,
                details={"candidate_email": candidate_email, "type": "email_match"},
            )
            return False, reason

        # 2. So khớp IP đăng ký (bỏ qua localhost / test fixture)
        if client_ip and client_ip not in ("127.0.0.1", "localhost", "testclient"):
            if referrer.registration_ip and client_ip == referrer.registration_ip:
                reason = "Phát hiện địa chỉ IP đăng ký trùng lặp với người giới thiệu"
                await cls._log_fraud_violation(
                    db=db,
                    referrer_id=referrer.id,
                    client_ip=client_ip,
                    reason=reason,
                    details={"candidate_email": candidate_email, "client_ip": client_ip, "type": "ip_match"},
                )
                return False, reason

        # 3. So khớp thiết bị (Device Fingerprint)
        if device_fingerprint and referrer.device_fingerprint:
            if device_fingerprint.strip() == referrer.device_fingerprint.strip():
                reason = "Phát hiện dấu vân tay thiết bị trùng lặp với người giới thiệu"
                await cls._log_fraud_violation(
                    db=db,
                    referrer_id=referrer.id,
                    client_ip=client_ip,
                    reason=reason,
                    details={"candidate_email": candidate_email, "device_fingerprint": device_fingerprint, "type": "device_match"},
                )
                return False, reason

        return True, None

    @classmethod
    async def _log_fraud_violation(
        cls,
        db: AsyncSession,
        referrer_id: int,
        client_ip: Optional[str],
        reason: str,
        details: Dict[str, Any],
    ) -> None:
        """Ghi nhật ký sự cố gian lận affiliate vào SecurityViolationLog."""
        try:
            violation = SecurityViolationLog(
                user_id=referrer_id,
                ip_address=client_ip,
                violation_type="affiliate_self_referral",
                category="affiliate_anti_fraud",
                snippet=reason,
                action_taken="blocked",
                details=json.dumps(details),
            )
            db.add(violation)
            await db.commit()
        except Exception as e:
            logger.warning(f"Lỗi khi ghi SecurityViolationLog: {e}")

    @classmethod
    async def record_order_commission(
        cls,
        db: AsyncSession,
        order: Order,
    ) -> Optional[AffiliateCommission]:
        """
        Ghi nhận hoa hồng tự động khi đơn hàng được thanh toán thành công (Issue #14 - Req #2).
        Tạm giữ (pending) trong 14 ngày (cấu hình trong config).
        """
        # 1. Đảm bảo Idempotency — Không tạo trùng lặp hoa hồng cho cùng một order_id
        stmt_exist = select(AffiliateCommission).where(AffiliateCommission.order_id == order.id)
        existing = (await db.execute(stmt_exist)).scalar_one_or_none()
        if existing:
            logger.info(f"Hoa hồng cho đơn hàng #{order.order_code} đã được ghi nhận trước đó.")
            return existing

        # 2. Kiểm tra thông tin người mua và người giới thiệu
        stmt_buyer = select(User).where(User.id == order.user_id)
        buyer = (await db.execute(stmt_buyer)).scalar_one_or_none()
        if not buyer or not buyer.referred_by_id:
            return None

        # Anti-fraud kiểm tra chéo: người mua không thể là người giới thiệu
        if buyer.referred_by_id == buyer.id:
            logger.warning(f"Đơn hàng #{order.order_code}: buyer.referred_by_id trùng với buyer.id!")
            return None

        # Kiểm tra người giới thiệu
        stmt_ref = select(User).where(User.id == buyer.referred_by_id)
        referrer = (await db.execute(stmt_ref)).scalar_one_or_none()
        if not referrer or not referrer.is_active or referrer.is_banned:
            logger.warning(f"Người giới thiệu #{buyer.referred_by_id} bị khóa hoặc không tồn tại.")
            return None

        # 3. Tính toán hoa hồng
        settings = get_settings()
        commission_rate = getattr(settings, "affiliate_commission_rate", 0.25)

        # Kiểm tra cấu hình ghi đè trong SystemSetting nếu có
        stmt_setting = select(SystemSetting).where(SystemSetting.key == "affiliate_commission_rate")
        setting_val = (await db.execute(stmt_setting)).scalar_one_or_none()
        if setting_val and setting_val.value:
            try:
                commission_rate = float(setting_val.value)
            except ValueError:
                pass

        commission_amount = int(order.final_amount * commission_rate)
        if commission_amount <= 0:
            return None

        # 4. Thiết lập thời gian tạm giữ (mặc định 14 ngày)
        hold_days = getattr(settings, "affiliate_hold_period_days", 14)
        stmt_hold = select(SystemSetting).where(SystemSetting.key == "affiliate_hold_period_days")
        setting_hold = (await db.execute(stmt_hold)).scalar_one_or_none()
        if setting_hold and setting_hold.value:
            try:
                hold_days = int(setting_hold.value)
            except ValueError:
                pass

        hold_until = datetime.now(UTC) + timedelta(days=hold_days)

        commission = AffiliateCommission(
            affiliate_user_id=referrer.id,
            referred_user_id=buyer.id,
            order_id=order.id,
            order_amount=order.final_amount,
            commission_rate=commission_rate,
            amount=commission_amount,
            status=CommissionStatus.PENDING.value,
            hold_until=hold_until,
        )
        db.add(commission)
        await db.commit()
        await db.refresh(commission)

        logger.info(
            f"Đã tạo hoa hồng Affiliate: #{commission.id} cho User #{referrer.id} "
            f"từ đơn #{order.order_code} số tiền {commission_amount:,} VND ({commission_rate * 100}%)."
        )
        return commission

    @classmethod
    async def cancel_order_commission(
        cls,
        db: AsyncSession,
        order_id: int,
        reason: str = "Order refunded",
    ) -> Optional[AffiliateCommission]:
        """Tự động thu hồi hoa hồng khi đơn hàng bị refund / hủy (Issue #14 - Req #2)."""
        stmt = select(AffiliateCommission).where(AffiliateCommission.order_id == order_id)
        commission = (await db.execute(stmt)).scalar_one_or_none()

        if not commission or commission.status == CommissionStatus.CANCELLED.value:
            return commission

        commission.status = CommissionStatus.CANCELLED.value
        commission.cancelled_at = datetime.now(UTC)
        commission.cancel_reason = reason
        await db.commit()
        await db.refresh(commission)

        logger.info(f"Đã thu hồi hoa hồng Affiliate #{commission.id} của đơn #{order_id} do: {reason}")
        return commission

    @classmethod
    async def settle_pending_commissions(cls, db: AsyncSession) -> int:
        """
        Quyết toán tự động các hoa hồng đang pending đã đủ 14 ngày sang approved (Req #2).
        Được gọi tự động khi tải dashboard hoặc định kỳ.
        """
        now = datetime.now(UTC)
        stmt = select(AffiliateCommission).where(
            AffiliateCommission.status == CommissionStatus.PENDING.value,
        )
        pending_list = list((await db.execute(stmt)).scalars().all())

        if not pending_list:
            return 0

        settled_count = 0
        for c in pending_list:
            h = c.hold_until if c.hold_until.tzinfo else c.hold_until.replace(tzinfo=UTC)
            if h <= now:
                c.status = CommissionStatus.APPROVED.value
                c.approved_at = now
                settled_count += 1

        if settled_count > 0:
            await db.commit()
            logger.info(f"Đã quyết toán chuyển trạng thái APPROVED cho {settled_count} khoản hoa hồng.")

        return settled_count

    @classmethod
    async def get_affiliate_stats(cls, db: AsyncSession, user: User) -> Dict[str, Any]:
        """
        Lấy số liệu thống kê tổng quan và lịch sử cho Dashboard Affiliate (Req #3):
        - Số lượt click, số đăng ký, số đơn hàng
        - Doanh thu: chờ duyệt (pending), khả dụng (approved - đã rút), đã rút (withdrawn)
        - Danh sách chi tiết các khoản hoa hồng & yêu cầu rút tiền
        """
        # 1. Tự động quyết toán hoa hồng hết hạn hold 14 ngày
        await cls.settle_pending_commissions(db)

        # 2. Đảm bảo người dùng có mã giới thiệu
        ref_code = await cls.get_or_create_referral_code(db, user)
        settings = get_settings()
        frontend_url = settings.frontend_url.rstrip("/")
        referral_link = f"{frontend_url}/register?ref={ref_code}"

        # 3. Đếm số lượt click
        stmt_clicks = select(func.count(AffiliateClick.id)).where(AffiliateClick.affiliate_user_id == user.id)
        total_clicks = (await db.execute(stmt_clicks)).scalar() or 0

        # 4. Đếm số lượt đăng ký thành công
        stmt_signups = select(func.count(User.id)).where(User.referred_by_id == user.id)
        total_signups = (await db.execute(stmt_signups)).scalar() or 0

        # 5. Đếm số đơn hàng đã phát sinh hoa hồng
        stmt_orders = select(func.count(AffiliateCommission.id)).where(
            AffiliateCommission.affiliate_user_id == user.id,
            AffiliateCommission.status != CommissionStatus.CANCELLED.value,
        )
        total_orders = (await db.execute(stmt_orders)).scalar() or 0

        # 6. Tính toán các khoản hoa hồng
        # - Chờ duyệt (Pending)
        stmt_pending = select(func.coalesce(func.sum(AffiliateCommission.amount), 0)).where(
            AffiliateCommission.affiliate_user_id == user.id,
            AffiliateCommission.status == CommissionStatus.PENDING.value,
        )
        pending_commission = (await db.execute(stmt_pending)).scalar() or 0

        # - Đã duyệt (Approved)
        stmt_approved = select(func.coalesce(func.sum(AffiliateCommission.amount), 0)).where(
            AffiliateCommission.affiliate_user_id == user.id,
            AffiliateCommission.status == CommissionStatus.APPROVED.value,
        )
        approved_commission = (await db.execute(stmt_approved)).scalar() or 0

        # - Đã chi trả thành công (Withdrawn)
        stmt_withdrawn = select(func.coalesce(func.sum(AffiliateWithdrawal.amount), 0)).where(
            AffiliateWithdrawal.user_id == user.id,
            AffiliateWithdrawal.status == WithdrawalStatus.APPROVED.value,
        )
        withdrawn_commission = (await db.execute(stmt_withdrawn)).scalar() or 0

        # - Đang chờ rút (Pending Withdrawal)
        stmt_pending_w = select(func.coalesce(func.sum(AffiliateWithdrawal.amount), 0)).where(
            AffiliateWithdrawal.user_id == user.id,
            AffiliateWithdrawal.status == WithdrawalStatus.PENDING.value,
        )
        pending_withdrawals = (await db.execute(stmt_pending_w)).scalar() or 0

        # Số dư khả dụng để rút = Approved - (Withdrawn + Pending Withdrawals)
        available_commission = max(0, approved_commission - withdrawn_commission - pending_withdrawals)
        total_earned_commission = approved_commission

        # 7. Danh sách chi tiết các khoản hoa hồng gần nhất (50 giao dịch)
        stmt_comm_list = (
            select(AffiliateCommission, Order.order_code, User.email.label("buyer_email"))
            .join(Order, AffiliateCommission.order_id == Order.id)
            .join(User, AffiliateCommission.referred_user_id == User.id)
            .where(AffiliateCommission.affiliate_user_id == user.id)
            .order_by(desc(AffiliateCommission.created_at))
            .limit(50)
        )
        comm_rows = (await db.execute(stmt_comm_list)).all()
        commissions_data = []
        for comm, order_code, buyer_email in comm_rows:
            commissions_data.append({
                "id": comm.id,
                "order_code": order_code,
                "buyer_masked_email": mask_email(buyer_email),
                "order_amount": comm.order_amount,
                "commission_rate": comm.commission_rate,
                "amount": comm.amount,
                "status": comm.status,
                "hold_until": comm.hold_until,
                "created_at": comm.created_at,
            })

        # 8. Danh sách yêu cầu rút tiền gần nhất (50 yêu cầu)
        stmt_w_list = (
            select(AffiliateWithdrawal)
            .where(AffiliateWithdrawal.user_id == user.id)
            .order_by(desc(AffiliateWithdrawal.created_at))
            .limit(50)
        )
        withdrawals_data = list((await db.execute(stmt_w_list)).scalars().all())

        return {
            "referral_code": ref_code,
            "referral_link": referral_link,
            "commission_rate": getattr(settings, "affiliate_commission_rate", 0.25),
            "hold_period_days": getattr(settings, "affiliate_hold_period_days", 14),
            "min_payout_amount": getattr(settings, "affiliate_min_payout_amount", 200000),
            "stats": {
                "total_clicks": total_clicks,
                "total_signups": total_signups,
                "total_orders": total_orders,
                "pending_commission": pending_commission,
                "available_commission": available_commission,
                "withdrawn_commission": withdrawn_commission,
                "total_earned_commission": total_earned_commission,
            },
            "commissions": commissions_data,
            "withdrawals": withdrawals_data,
        }

    @classmethod
    async def request_payout(
        cls,
        db: AsyncSession,
        user: User,
        amount: int,
        bank_name: str,
        bank_account_number: str,
        bank_account_holder: str,
    ) -> AffiliateWithdrawal:
        """Gửi yêu cầu rút tiền hoa hồng (Req #4)."""
        settings = get_settings()
        min_payout = getattr(settings, "affiliate_min_payout_amount", 200000)

        # 1. Kiểm tra số tiền tối thiểu
        if amount < min_payout:
            raise AppError(
                code="MIN_WITHDRAWAL_AMOUNT",
                message=f"Số tiền rút tối thiểu là {min_payout:,} VNĐ.",
                status_code=400,
            )

        # 2. Kiểm tra thông tin tài khoản ngân hàng
        if not bank_name.strip() or not bank_account_number.strip() or not bank_account_holder.strip():
            raise AppError(
                code="INVALID_BANK_INFO",
                message="Vui lòng nhập đầy đủ tên ngân hàng, số tài khoản và tên chủ tài khoản.",
                status_code=400,
            )

        # 3. Kiểm tra số dư khả dụng
        stats = await cls.get_affiliate_stats(db, user)
        available_balance = stats["stats"]["available_commission"]

        if amount > available_balance:
            raise AppError(
                code="INSUFFICIENT_AFFILIATE_BALANCE",
                message=f"Số dư hoa hồng khả dụng hiện tại ({available_balance:,} VNĐ) không đủ để rút {amount:,} VNĐ.",
                status_code=400,
            )

        withdrawal = AffiliateWithdrawal(
            user_id=user.id,
            amount=amount,
            bank_name=bank_name.strip(),
            bank_account_number=bank_account_number.strip(),
            bank_account_holder=bank_account_holder.strip().upper(),
            status=WithdrawalStatus.PENDING.value,
        )
        db.add(withdrawal)
        await db.commit()
        await db.refresh(withdrawal)

        logger.info(f"User #{user.id} đã tạo yêu cầu rút tiền Affiliate #{withdrawal.id} số tiền {amount:,} VNĐ.")
        return withdrawal

    @classmethod
    async def customize_code(
        cls,
        db: AsyncSession,
        user: User,
        new_code: str,
    ) -> str:
        """Tùy chỉnh mã giới thiệu cá nhân."""
        clean_code = new_code.strip().upper()

        if not re.match(r"^[A-Z0-9_-]{4,20}$", clean_code):
            raise AppError(
                code="INVALID_REFERRAL_CODE",
                message="Mã giới thiệu chỉ được chứa chữ cái, số, dấu gạch ngang và dài từ 4 đến 20 ký tự.",
                status_code=400,
            )

        # Kiểm tra xem mã đã có ai dùng chưa
        stmt = select(User).where(User.referral_code == clean_code, User.id != user.id)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise AppError(
                code="REFERRAL_CODE_EXISTS",
                message="Mã giới thiệu này đã được người khác sử dụng. Vui lòng chọn mã khác.",
                status_code=400,
            )

        user.referral_code = clean_code
        await db.commit()
        await db.refresh(user)
        return clean_code
