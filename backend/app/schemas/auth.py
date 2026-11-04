"""Pydantic schemas cho xác thực tài khoản và người dùng."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Mật khẩu ít nhất 6 ký tự")
    full_name: Optional[str] = Field(default=None, max_length=150)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    credential: str = Field(..., description="Google ID Token nhận từ Google Identity Services")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Mã token đặt lại mật khẩu")
    new_password: str = Field(..., min_length=6, description="Mật khẩu mới ít nhất 6 ký tự")


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    credits: int
    credit_balance: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class MessageResponse(BaseModel):
    message: str
