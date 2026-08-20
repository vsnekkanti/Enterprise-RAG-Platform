from fastapi import HTTPException, Depends, Header
from typing import Optional
from sqlalchemy.orm import joinedload
from src.storage.db import get_db
from src.storage.models import User

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    token = authorization.replace("Bearer ", "")
    db = get_db()
    user = db.query(User).options(joinedload(User.acl_groups)).filter(
        User.api_token == token
    ).first()
    if not user:
        db.close()
        raise HTTPException(status_code=401, detail="Invalid token")
    result = {
        "id": user.id,
        "username": user.username,
        "acl_groups": [g.name for g in user.acl_groups]
    }
    db.close()
    return result

async def get_user_acl_groups(user: dict = Depends(get_current_user)) -> list:
    return user["acl_groups"]
