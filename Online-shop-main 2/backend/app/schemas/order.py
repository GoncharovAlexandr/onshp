from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    price: float

class OrderCreate(BaseModel):
    customer_id: int
    items: List[OrderItemBase] = []

class OrderOut(BaseModel):
    id: int
    customer_id: int
    order_date: datetime
    total_amount: float
    status: str
    items: List[OrderItemBase] = []

    class Config:
        orm_mode = True