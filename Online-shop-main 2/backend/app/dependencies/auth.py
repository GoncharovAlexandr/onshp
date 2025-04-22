from fastapi import HTTPException, Depends, Cookie
from redis.asyncio import Redis
import json
import logging
from backend.app.db.redis import get_redis

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def get_current_admin(session_id: str = Cookie(default=None), redis: Redis = Depends(get_redis)):
    logger.debug(f"Admin Session ID: {session_id}")
    if not session_id:
        logger.debug("No admin session ID provided")
        raise HTTPException(status_code=401, detail="Missing session_id")
    session_data = await redis.get(f"session:{session_id}")
    logger.debug(f"Admin Session data: {session_data}")
    if not session_data:
        logger.debug("Invalid or expired admin session")
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    try:
        session = json.loads(session_data)
    except json.JSONDecodeError:
        logger.error("Failed to decode session data")
        raise HTTPException(status_code=401, detail="Invalid session data")
    if "admin_id" not in session:
        raise HTTPException(status_code=403, detail="Not an admin session")
    return session

async def get_current_user(session_id: str = Cookie(default=None), redis: Redis = Depends(get_redis)):
    logger.debug(f"User Session ID: {session_id}")
    if not session_id:
        logger.debug("No user session ID provided")
        raise HTTPException(status_code=401, detail="No session ID provided")
    session_data = await redis.get(f"session:{session_id}")
    logger.debug(f"User Session data: {session_data}")
    if session_data is None:
        logger.debug("Invalid user session ID")
        raise HTTPException(status_code=401, detail="Invalid session ID")
    try:
        session_info = json.loads(session_data)
    except json.JSONDecodeError:
        logger.error("Failed to decode user session data")
        raise HTTPException(status_code=401, detail="Invalid session data")
    return {
        "id": session_info.get("customer_id"),
        "last_activity": session_info.get("last_activity"),
        "is_admin": "admin_id" in session_info
    }
