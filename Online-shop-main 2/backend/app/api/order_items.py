from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from backend.app.db.postgres import get_db
from backend.app.models.postgres_models import OrderItem
from backend.app.schemas.order_item import OrderItemIn, OrderItemOut, OrderItemUpdate
from typing import List

router = APIRouter()

@router.get("/", response_model=List[OrderItemOut])
async def get_all_order_items(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OrderItem))
    return result.scalars().all()

@router.get("/{item_id}", response_model=OrderItemOut)
async def get_order_item(item_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(OrderItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")
    return item

@router.post("/", response_model=OrderItemOut, status_code=201)
async def create_order_item(data: OrderItemIn, db: AsyncSession = Depends(get_db)):
    item = OrderItem(**data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.put("/{item_id}", response_model=OrderItemOut)
async def update_order_item(item_id: int, data: OrderItemUpdate, db: AsyncSession = Depends(get_db)):
    item = await db.get(OrderItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")
    update_data = data.model_dump(exclude_unset=True)
    await db.execute(update(OrderItem).where(OrderItem.id == item_id).values(**update_data))
    await db.commit()
    return await db.get(OrderItem, item_id)

@router.delete("/{item_id}", status_code=204)
async def delete_order_item(item_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(OrderItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")
    await db.execute(delete(OrderItem).where(OrderItem.id == item_id))
    await db.commit()
    return None