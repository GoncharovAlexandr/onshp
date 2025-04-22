from pydantic import BaseModel
from typing import List, Dict, Optional


class UserProfileBase(BaseModel):
    preferences: Optional[Dict] = {}
    recent_views: List[int] = []
    wishlist: List[int] = []

class UserProfileCreate(UserProfileBase):
    customer_id: str

class UserProfileOut(UserProfileBase):
    customer_id: str


class UserProfileUpdate(BaseModel):
    preferences: Optional[Dict] = None
