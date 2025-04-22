from fastapi import APIRouter, Depends, HTTPException
from backend.app.schemas.promotion import PromotionCreate, PromotionOut
from backend.app.db.mongo import db, get_all_promotions, get_promotion, create_promotion, delete_promotion, get_mongo_db
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from pymongo.database import Database
from backend.app.db.postgres import get_db

router = APIRouter()

def read_promotions(db: Database = Depends(get_mongo_db)):
    return get_all_promotions(db)


@router.get("/{promo_id}", response_model=PromotionOut)
def read_promotion(promo_id: str):
    promo = get_promotion(db, promo_id)
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return promo


@router.post("/", response_model=PromotionOut, status_code=201)
async def create_new_promotion(
    data: PromotionCreate,
    db_pg: AsyncSession = Depends(get_db)
):
    if data.products:
        result = await db_pg.execute(select(Product.id).where(Product.id.in_(data.products)))
        existing_ids = set(row[0] for row in result.all())
        missing = set(data.products) - existing_ids
        if missing:
            raise HTTPException(status_code=400, detail=f"Products not found: {list(missing)}")
    
    return create_promotion(db, data.dict())


@router.delete("/{promo_id}", status_code=204)
def delete_existing_promotion(promo_id: str):
    delete_promotion(db, promo_id)
