from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import secrets
from pwdlib import PasswordHash
from email.message import EmailMessage
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.rate_limit import RateLimitError, acquire_verification_send_quota
import aiosmtplib
from datetime import datetime, timedelta, timezone
import jwt
from dataclasses import dataclass

logger = get_logger()

password_hash = PasswordHash.recommended()

class EmailVerifyCodeError(Exception):
    pass

class UserAlreadyExistsError(Exception):
    pass

class UserNotFoundError(Exception):
    pass

class InvalidPasswordError(Exception):
    pass

class InvalidTokenError(Exception):
    pass


async def create_user_service(
    email:str,
    password:str,
    verify_code:str,
    redis:Redis,
    session:AsyncSession,
)->User:
    code_key = f"register:code:{email}"
    code = await redis.get(code_key)
    if code is None or code != verify_code:
        raise EmailVerifyCodeError
    existing_user = await session.execute(select(User).where(User.email == email))
    if existing_user.scalar_one_or_none() is not None:
        raise UserAlreadyExistsError
    user = User(
        email=email,
        password_hash=password_hash.hash(password),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise UserAlreadyExistsError
    await redis.delete(code_key)
    return user

async def send_verify_email_service(
    email: str,
    redis: Redis,
    ip: str,
) -> None:
    try:
        await acquire_verification_send_quota(redis, email, ip)
    except RateLimitError:
        logger.warning("register code rate limited email=%s ip=%s", email, ip)
        raise
    code = f"{secrets.randbelow(1_000_000):06d}"
    code_key = f"register:code:{email}"
    await redis.set(code_key, code, ex=60 * 5)
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = email
    message["Subject"] = "注册验证码"
    message.set_content(
        f"你正在注册账户，验证码是 {code}。\n"
        "验证码 5 分钟内有效，请勿告诉他人。\n"
        "如果这不是你本人的操作，请忽略这封邮件。\n"
    )
    message.add_alternative(
        f"""\
<html>
  <body style="font-family: sans-serif; color: #222;">
    <p>你正在注册账户，验证码是：</p>
    <p style="font-size: 28px; letter-spacing: 6px; text-indent: 6px; font-weight: 700; text-align: center;">{code}</p>
    <p>验证码 5 分钟内有效，请勿告诉他人。</p>
    <p style="color: #666;">如果这不是你本人的操作，请忽略这封邮件。</p>
  </body>
</html>
""",
        subtype="html",
    )
    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            start_tls=True,
        )
    except aiosmtplib.SMTPException:
        await redis.delete(code_key)
        raise

async def send_reset_password_verification_code_service(
    email: str,
    redis: Redis,
    session: AsyncSession,
    ip: str,
) -> None:
    try:
        await acquire_verification_send_quota(redis, email, ip)
    except RateLimitError:
        logger.warning("reset code rate limited email=%s ip=%s", email, ip)
        raise
    result = await session.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none() is None:
        raise UserNotFoundError
    code = f"{secrets.randbelow(1_000_000):06d}"
    code_key = f"reset:code:{email}"
    await redis.set(code_key, code, ex=60 * 5)
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = email
    message["Subject"] = "重置密码验证码"
    message.set_content(
        f"你正在重置密码，验证码是 {code}。\n"
        "验证码 5 分钟内有效，请勿告诉他人。\n"
        "如果这不是你本人的操作，请忽略这封邮件。\n"
    )
    message.add_alternative(
        f"""\
<html>
  <body style="font-family: sans-serif; color: #222;">
    <p>你正在重置密码，验证码是：</p>
    <p style="font-size: 28px; letter-spacing: 6px; text-indent: 6px; font-weight: 700; text-align: center;">{code}</p>
    <p>验证码 5 分钟内有效，请勿告诉他人。</p>
    <p style="color: #666;">如果这不是你本人的操作，请忽略这封邮件。</p>
  </body>
</html>
""",
        subtype="html",
    )
    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            start_tls=True,
        )
    except aiosmtplib.SMTPException:
        await redis.delete(code_key)
        raise

@dataclass(frozen=True)
class IssuedToken:
    access_token:str
    refresh_token:str
    token_type:str
    expires_in:float

async def _issue_tokens(user_id:int,redis:Redis)->IssuedToken:
    access_expires = timedelta(minutes=settings.jwt_access_token_expires_minutes)
    refresh_expires = timedelta(days=settings.jwt_refresh_token_expires_days)
    access_token = create_token(user_id,"access",access_expires)
    refresh_token = create_token(user_id,"refresh",refresh_expires)
    await redis.set(
        f"token:refresh:{user_id}",
        refresh_token,
        ex=int(refresh_expires.total_seconds()),
    )
    return IssuedToken(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=access_expires.total_seconds(),
    )

async def login_user_service(
    email:str,
    password:str,
    session:AsyncSession,
    redis:Redis,
):
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundError
    if not password_hash.verify(password,user.password_hash):
        raise InvalidPasswordError
    return await _issue_tokens(user.id,redis)


def create_token(user_id:int,token_type:str,expires_delta:timedelta)->str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub":str(user_id),
        "type":token_type,
        "exp":now + expires_delta,
        "iat":now,
    }
    return jwt.encode(payload,settings.jwt_secret,algorithm=settings.jwt_algorithm)

async def reset_password_service(
    email:str,
    new_password:str,
    verification_code:str,
    session:AsyncSession,
    redis:Redis,
)->None:
    code_key = f"reset:code:{email}"
    code = await redis.get(code_key)
    if code is None or code != verification_code:
        raise EmailVerifyCodeError
    existing_user = await session.execute(select(User).where(User.email == email))
    user = existing_user.scalar_one_or_none()
    if user is None:
        raise UserNotFoundError
    user.password_hash = password_hash.hash(new_password)
    await session.commit()
    await redis.delete(code_key)
    await redis.delete(f"token:refresh:{user.id}")
    logger.info("password reset revoked refresh token user_id=%s", user.id)


async def logout_user_service(
    refresh_token:str,
    redis:Redis,
)->None:
    try:
        payload = jwt.decode(
            refresh_token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
    except jwt.InvalidTokenError:
        raise InvalidTokenError
    if payload["type"] != "refresh":
        raise InvalidTokenError
    key = f"token:refresh:{payload['sub']}"
    stored = await redis.get(key)
    if stored is None or stored != refresh_token:
        return 
    await redis.delete(key) 

async def refresh_token_service(
    refresh_token:str,
    session:AsyncSession,
    redis:Redis,
)->IssuedToken:
    try:
        payload = jwt.decode(
            refresh_token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
    except jwt.InvalidTokenError:
        raise InvalidTokenError
    if payload["type"] != "refresh":
        raise InvalidTokenError
    user_id = int(payload["sub"])
    stored = await redis.get(f"token:refresh:{user_id}")
    if stored is None or stored != refresh_token:
        raise InvalidTokenError
    result =await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise InvalidTokenError
    return await _issue_tokens(user.id,redis)