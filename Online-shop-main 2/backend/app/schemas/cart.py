from pydantic import BaseModel
from typing import List

class CartItem(BaseModel):
    product_id: int
    quantity: int
    price: float

class CartCreate(BaseModel):
    customer_id: str
    items: List[CartItem] = []

class CartOut(BaseModel):
    customer_id: str
    items: List[CartItem]
