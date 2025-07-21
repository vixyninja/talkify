from fastapi import APIRouter, Depends, Response
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import UnauthorizedException
from ...core.schemas import TokenLogoutRequest
from ...core.security import blacklist_tokens, oauth2_scheme

router = APIRouter(tags=["login"])


@router.post("/logout")
async def logout(
    _: Response,
    token: TokenLogoutRequest,
    access_token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(async_get_db),
) -> dict[str, str]:
    try:
        if not token:
            raise UnauthorizedException("Refresh token not found")

        await blacklist_tokens(access_token=access_token, refresh_token=token.refresh_token, db=db)

        return {"message": "Logged out successfully"}

    except JWTError:
        raise UnauthorizedException("Invalid token.")
