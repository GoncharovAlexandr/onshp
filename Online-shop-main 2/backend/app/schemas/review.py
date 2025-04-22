from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ReviewIn(BaseModel):
    product_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: str

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None

class ReviewOut(BaseModel):
    id: int
    product_id: int
    customer_id: int
    rating: int
    comment: str
    created_at: datetime

    class Config:
        from_attributes = True
