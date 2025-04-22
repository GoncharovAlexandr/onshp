from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.app.db.postgres import get_db
from backend.app.db.redis import get_redis
from backend.app.models.postgres_models import Customer
from backend.app.schemas.user import UserRegister, UserLogin, UserOut
from passlib.context import CryptContext
from redis.asyncio import Redis
import uuid
import json
import logging
from datetime import datetime
from typing import Optional

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
templates = Jinja2Templates(directory="templates")
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@router.get("/register")
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(
        name: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        phone: Optional[str] = Form(None),
        address: Optional[str] = Form(None),
        db: AsyncSession = Depends(get_db)
):
    logger.debug(f"Attempting to register user: {email}")
    result = await db.execute(select(Customer).where(Customer.email == email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Создаём данные для Pydantic-модели
    user_data = UserRegister(
        name=name,
        email=email,
        password=password,
        phone=phone,
        address=address
    )

    hashed_password = pwd_context.hash(user_data.password)
    new_user = Customer(
        name=user_data.name,
        email=user_data.email,
        password=hashed_password,
        phone=user_data.phone,
        address=user_data.address
    )
    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to register user: {str(e)}")

    logger.info(f"User registered: {email}")
    return RedirectResponse(url="/user/auth/jwt/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/jwt/login")
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/jwt/login")
async def login_user(
        response: Response,
        username: str = Form(None),
        password: str = Form(None),
        user_data: UserLogin | None = None,
        db: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
):
    email = user_data.email if user_data else username
    pwd = user_data.password if user_data else password
    if not email or not pwd:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email and password are required")

    logger.debug(f"Attempting to login user: {email}")
    result = await db.execute(select(Customer).where(Customer.email == email))
    user = result.scalars().first()
    if not user or not pwd_context.verify(pwd, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    session_id = str(uuid.uuid4())
    session_data = {
        "customer_id": user.id,
        "last_activity": datetime.utcnow().isoformat()
    }
    try:
        await redis.set(f"session:{session_id}", json.dumps(session_data), ex=3600)
        logger.debug(f"Session created for user {email}: {session_id}")
    except Exception as e:
        logger.error(f"Redis error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create session")

    response.set_cookie(key="session_id", value=session_id, httponly=True)
    if user_data:  # JSON API
        return {"message": "Login successful", "session_id": session_id}
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)