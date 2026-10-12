from pydantic import BaseModel,EmailStr,Field
from datetime import datetime

class UserVerifyEmailRequest(BaseModel):
    email:EmailStr=Field(...,description="邮箱")

class UserCreateRequest(BaseModel):
    email:EmailStr=Field(...,description="邮箱")
    password:str=Field(...,min_length=8,max_length=128,description="密码")
    verification_code:str=Field(...,min_length=6,max_length=6,description="验证码")

class UserCreateResponse(BaseModel):
    id:int
    email:EmailStr
    created_at:datetime


