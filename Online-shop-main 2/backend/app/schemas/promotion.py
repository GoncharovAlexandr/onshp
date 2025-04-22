from pydantic import BaseModel
from typing import List


class PromotionBase(BaseModel):
    name: str
    description: str
    discount: float  # значение от 0 до 1
    products: List[int]


class PromotionCreate(PromotionBase):
    pass


class PromotionOut(PromotionBase):
    id: str
