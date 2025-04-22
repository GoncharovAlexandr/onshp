from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from backend.app.schemas.promotion import PromotionOut

class ProductBase(BaseModel):
    name: str
    price: float
    category_id: int
    stock_quantity: int = 0
    image: Optional[str] = None

class ProductIn(ProductBase):
    description: Optional[str] = None
    attributes: Optional[dict] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[int] = None
    stock_quantity: Optional[int] = None
    image: Optional[HttpUrl] = None
    description: Optional[str] = None
    attributes: Optional[dict] = None

class ProductOut(BaseModel):
    id: int
    name: str
    price: float
    category_id: int
    stock_quantity: int
    image: Optional[str]
    description: Optional[str]
    attributes: Optional[dict]
    promotions: Optional[List[PromotionOut]] = []

    class Config:
        from_attributes = True
