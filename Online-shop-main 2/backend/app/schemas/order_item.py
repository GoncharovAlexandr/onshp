from pydantic import BaseModel
from typing import Optional

class OrderItemIn(BaseModel):
    order_id: int
    product_id: int
    quantity: int
    price: float

class OrderItemUpdate(BaseModel):
    quantity: Optional[int] = None
    price: Optional[float] = None

class OrderItemOut(BaseModel):
    id: int
    order_id: int
    product_id: int
    quantity: int
    price: float

    class Config:
        from_attributes = True
