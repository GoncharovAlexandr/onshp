from fastapi import APIRouter, HTTPException, Depends, Response, Form, Request, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.hash import bcrypt
from uuid import uuid4
from datetime import datetime
import json
import logging
from backend.app.db.postgres import get_db
from backend.app.db.redis import get_redis
from backend.app.models.postgres_models import Admin
from backend.app.schemas.admin import AdminRegister, AdminLogin, AdminOut
from redis.asyncio import Redis
from backend.app.dependencies.auth import get_current_admin  # Импортируем зависимость

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@router.get("/register")
async def admin_register_form(request: Request):
    return templates.TemplateResponse("admin_register.html", {"request": request})

@router.post("/register", response_model=AdminOut)
async def register_admin(
    email: str = Form(None),
    password: str = Form(None),
    data: AdminRegister | None = None,
    db: AsyncSession = Depends(get_db)
):
    admin_email = data.email if data else email
    admin_password = data.password if data else password
    logger.debug(f"Attempting to register admin: {admin_email}")

    if not admin_email or not admin_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email and password are required")

    result = await db.execute(select(Admin).where(Admin.email == admin_email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed_password = bcrypt.hash(admin_password)
    new_admin = Admin(email=admin_email, password=hashed_password)

    try:
        db.add(new_admin)
        await db.commit()
        await db.refresh(new_admin)
        logger.debug(f"Admin {admin_email} registered successfully")
    except Exception as e:
        logger.error(f"Database error: {e}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to register admin")

    return new_admin

@router.get("/login")
async def admin_login_form(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

@router.post("/login")
async def login_admin(
    response: Response,
    email: str = Form(None),
    password: str = Form(None),
    data: AdminLogin | None = None,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    admin_email = data.email if data else email
    admin_password = data.password if data else password
    logger.debug(f"Attempting to login admin: {admin_email}")

    if not admin_email or not admin_password:
        logger.error("Missing email or password")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email and password are required")

    result = await db.execute(select(Admin).where(Admin.email == admin_email))
    admin = result.scalar_one_or_none()

    if not admin or not bcrypt.verify(admin_password, admin.password):
        logger.error(f"Invalid credentials for {admin_email}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Check for existing session
    async for key in redis.scan_iter("session:*"):
        session_data = await redis.get(key)
        if session_data:
            session = json.loads(session_data)
            if session.get("admin_id") == admin.id:
                session["last_activity"] = datetime.utcnow().isoformat()
                await redis.setex(key, 3600, json.dumps(session))
                session_id = key.split(":")[1]
                response.set_cookie(
                    key="session_id",
                    value=session_id,
                    httponly=True,
                    samesite="lax",
                    secure=False,  # Установите True, если используете HTTPS
                    path="/"
                )
                logger.debug(f"Cookie set for existing session: session_id={session_id}")
                return {"session_id": session_id} if data else RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    # Create new session
    session_id = str(uuid4())
    session_data = {
        "admin_id": admin.id,
        "last_activity": datetime.utcnow().isoformat()
    }
    try:
        await redis.setex(f"session:{session_id}", 3600, json.dumps(session_data))
        logger.debug(f"Session created for admin {admin_email}: {session_id} (key: session:{session_id})")
    except Exception as e:
        logger.error(f"Redis error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create session")

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=False,  # Установите True, если используете HTTPS
        path="/"
    )
    logger.debug(f"Cookie set for new session: session_id={session_id}")
    return {"session_id": session_id} if data else RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/admin/protected")
async def protected_route(admin: dict = Depends(get_current_admin)):
    logger.debug(f"Admin accessing protected route: {admin}")
    return {"message": "This is a protected route", "admin": admin}
