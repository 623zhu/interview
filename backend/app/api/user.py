from fastapi import APIRouter,status,Request,HTTPException
from app.schemas.user import UserCreateRequest,UserCreateResponse,UserVerifyEmailRequest
from app.service.user import create_user_service,EmailVerifyCodeError,UserAlreadyExistsError,send_verify_email_service

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
                session)
            return UserCreateResponse.model_validate(user)
        except EmailVerifyCodeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="验证码不存在,过期或者不一致")
        except UserAlreadyExistsError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="该邮箱已注册")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(e))


@router.post(
    "/verification-codes",
    status_code=status.HTTP_201_CREATED,
    summary="邮箱注册码",
    description="发送邮箱注册验证码",
)
async def create_user_verify_email(body:UserVerifyEmailRequest,request:Request):
    try:
        await send_verify_email_service(body.email,request.app.state.redis_client)
        return {"message":"验证码发送成功"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(e))