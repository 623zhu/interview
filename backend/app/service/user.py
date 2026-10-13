from socket import AI_NUMERICHOST
from turtle import home
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import random
import secrets
from pwdlib import PasswordHash
from email.message import EmailMessage
from app.core.config import settings
import aiosmtplib

password_hash = PasswordHash.recommended()

class EmailVerifyCodeError(Exception):
    pass

class UserAlreadyExistsError(Exception):
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
    if code is None or code.decode() != verify_code:
        raise EmailVerifyCodeError
    existing_user = await session.execute(select(User).where(User.email == email))
    if existing_user.scalar_one_or_none() is not None:
        raise UserAlreadyExistsError
    user = User(
        email=email,
        password=password_hash.hash(password),
        verify_code=verify_code,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise UserAlreadyExistsError
    await redis.delete()
    return user

async def send_verify_email_service(
    email:str,
    redis:Redis,
)->None:
    code = str(random.randint(100000, 999999))
    code_key = f"register:code:{email}"
    await redis.set(code_key,code,ex=60*5)

    message = EmailMessage()
    message['From'] = settings.smtp_from
    message['To'] = email
    message['Subject'] = "验证码"
    message.set_content(
    f"你正在注册账号，验证码是 {code}。\n"
    "验证码 5 分钟内有效，请勿告诉他人。\n"
    "如果这不是你本人的操作，请忽略这封邮件。\n"
)
    message.add_alternative(
    f"""\
<html>
  <body style="font-family: sans-serif; color: #222;">
    <p>你正在注册账号，验证码是：</p>
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
    except aiosmtplib.SMTPException as e:
        await redis.delete(code_key)
        raise 