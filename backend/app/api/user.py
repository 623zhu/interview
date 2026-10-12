from fastapi import APIRouter,status

router = APIRouter(prefix="/api/v1/users",tags=["users"])

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="注册用户",
    description="注册新用户")
async def create_user():
    return {"message":"User created successfully"}


@router.post(
    "/verification-codes",
    status_code=status.HTTP_201_CREATED,
    summary="邮箱注册码",
    description="发送邮箱注册验证码",
)
async def create_user_verify_email():
    return {"message":"Email verified successfully"}