from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pymongo.database import Database
from typing import Optional
import logging

from backend.app.db.mongo import get_mongo_db, get_user_profile, update_user_profile
from backend.app.schemas.user_profile import UserProfileOut, UserProfileUpdate
from backend.app.dependencies.auth import get_current_user

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/html")
async def get_profile_html(
    request: Request,
    user=Depends(get_current_user),
    db: Database = Depends(get_mongo_db)
):
    profile = get_user_profile(db, str(user["id"]))
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "profile": profile, "is_authenticated": True}
    )

@router.post("/", response_model=UserProfileOut)
async def update_profile_form(
    name: str = Form(...),
    email: str = Form(...),
    bio: Optional[str] = Form(""),
    user=Depends(get_current_user),
    db: Database = Depends(get_mongo_db)
):
    logger.info(f"Updating profile for user_id={user['id']}, name={name}, email={email}, bio={bio}")
    update_data = {"name": name, "email": email, "bio": bio if bio else None}
    profile = update_user_profile(db, str(user["id"]), update_data)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    logger.info(f"Profile updated for user_id={user['id']}")
    return RedirectResponse(url="/profile/html", status_code=303)

@router.get("/", response_model=UserProfileOut)
async def read_user_profile(user=Depends(get_current_user), db: Database = Depends(get_mongo_db)):
    profile = get_user_profile(db, str(user["id"]))
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.put("/", response_model=UserProfileOut)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    user=Depends(get_current_user),
    db: Database = Depends(get_mongo_db)
):
    update_data = profile_data.dict(exclude_unset=True)
    profile = update_user_profile(db, str(user["id"]), update_data)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile