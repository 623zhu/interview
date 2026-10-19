from typing import Annotated
from fastapi import Depends, HTTPException, status,Header,Request
from app.models.user import User
from app.core.security import decode_access_token
from sqlalchemy import select
import jwt




async def get_current_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if authorization is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Unauthorized")
    scheme,_,token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Unauthorized")
    try:
        user_id = decode_access_token(token)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Unauthorized")
    async with request.app.state.mysql_session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Unauthorized")
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]
