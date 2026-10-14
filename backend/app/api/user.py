from fastapi import APIRouter,status,Request,HTTPException
from app.schemas.user import (
    UserCreateRequest,UserCreateResponse,
    UserVerifyEmailRequest,UserLoginRequest,UserLoginResponse,
    ResetPasswordRequest,ResetPasswordResponse,ResetPasswordVerificationCodeRequest
)

from app.service.user import (
    create_user_service,login_user_service,reset_password_service,
    send_verify_email_service,send_reset_password_verification_code_service,
    EmailVerifyCodeError,UserAlreadyExistsError,
    UserNotFoundError,InvalidPasswordError,
)

router = APIRouter(prefix="/api/v1/users",tags=["users"])

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="注册用户",
    description="注册新用户",
    )
async def create_user(body:UserCreateRequest,request:Request)-> UserCreateResponse:
    async with request.app.state.mysql_session_factory() as session:
        try:
            user = await create_user_service(
                body.email,
                body.password,
                body.verification_code,
                request.app.state.redis_client,
                session
                )
            return UserCreateResponse.model_validate(user)
        except EmailVerifyCodeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="验证码不存在,过期或者不一致")
        except UserAlreadyExistsError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="该邮箱已注册")

@router.post(
    "/verification-codes",
    status_code=status.HTTP_201_CREATED,
    summary="邮箱注册码",
    description="发送邮箱注册验证码",
)
async def create_user_verify_email(body:UserVerifyEmailRequest,request:Request):
    try:
        await send_verify_email_service(
            body.email,
            request.app.state.redis_client,
        )
        return {}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(e))


@router.post(
    "/session",
    summary="登录",
    description="登录用户",
    status_code=status.HTTP_200_OK,
)
async def login_user(body:UserLoginRequest,request:Request)->UserLoginResponse:
    async with request.app.state.mysql_session_factory() as session:
        try:
            issued_token = await login_user_service(body.email,body.password,session)
            return UserLoginResponse(
                access_token=issued_token.access_token,
                refresh_token=issued_token.refresh_token,
                token_type=issued_token.token_type,
                expires_in=int(issued_token.expires_in),
            )
        except UserNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="用户不存在")
        except InvalidPasswordError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="邮箱或密码错误")

@router.post(
    "/password-reset",
    summary="重置密码",
    description="校验验证码并重置密码",
    status_code=status.HTTP_200_OK,
)
async def reset_password(body:ResetPasswordRequest,request:Request)->ResetPasswordResponse:
    async with request.app.state.mysql_session_factory() as session:
        try:
            await reset_password_service(body.email,body.new_password,body.verification_code,session,request.app.state.redis_client)
            return ResetPasswordResponse(message="密码重置成功")
        except EmailVerifyCodeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="验证码不存在,过期或者不一致")
        except UserNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="用户不存在")


@router.post(
    "/password-reset/verification-codes",
    summary="重置密码验证码",
    description="发送重置密码验证码",
    status_code=status.HTTP_201_CREATED,
)
async def send_reset_password_verification_code(body:ResetPasswordVerificationCodeRequest,request:Request):
    try:
        async with request.app.state.mysql_session_factory() as session:
            await send_reset_password_verification_code_service(
                body.email,
                request.app.state.redis_client,
                session
        )
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="用户不存在")
    return {}