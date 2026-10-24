from pydantic import BaseModel,EmailStr,Field,ConfigDict
from datetime import datetime

class UserVerifyEmailRequest(BaseModel):
    email:EmailStr=Field(...,description="邮箱")


class UserCreateRequest(BaseModel):
    email:EmailStr=Field(...,description="邮箱")
    password:str=Field(...,min_length=8,max_length=128,description="密码")
    verification_code:str=Field(...,min_length=6,max_length=6,description="验证码")

class UserCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:int
    email:EmailStr
    created_at:datetime

class UserLoginRequest(BaseModel):    
    email:EmailStr=Field(...,description="邮箱")
    password:str=Field(...,min_length=8,max_length=128,description="密码")

class UserLoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    access_token:str
    refresh_token:str
    token_type:str
    expires_in:int
 
class ResetPasswordRequest(BaseModel):
    email:EmailStr=Field(...,description="邮箱")
    new_password:str=Field(...,min_length=8,max_length=128,description="新密码")
    verification_code:str=Field(...,min_length=6,max_length=6,description="验证码")

class ResetPasswordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    message:str

class ResetPasswordVerificationCodeRequest(BaseModel):
    email:EmailStr=Field(...,description="邮箱")


class LogoutRequest(BaseModel):
    refresh_token:str=Field(...,description="刷新令牌")

class RefreshTokenRequest(BaseModel):
    refresh_token:str=Field(...,description="刷新令牌")
