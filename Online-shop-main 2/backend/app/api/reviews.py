from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Form
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List
from backend.app.db.postgres import get_db
from backend.app.models.postgres_models import Review, Product
from backend.app.schemas.review import ReviewIn, ReviewUpdate, ReviewOut
from backend.app.dependencies.auth import get_current_user

router = APIRouter()

@router.post("/", response_model=ReviewOut, status_code=201)
async def create_review(
    request: Request,
    product_id: int = Form(...),
    rating: int = Form(...),
    comment: str = Form(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    review_data = ReviewIn(product_id=product_id, rating=rating, comment=comment)
    review = Review(**review_data.dict(), customer_id=user["id"])
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return RedirectResponse(url=f"/products/{product_id}", status_code=303)

@router.get("/", response_model=List[ReviewOut])
async def get_reviews(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review))
    return result.scalars().all()

@router.get("/{review_id}", response_model=ReviewOut)
async def get_review(review_id: int, db: AsyncSession = Depends(get_db)):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Product not found")
    return review

@router.put("/{review_id}", response_model=ReviewOut)
async def update_review(
    review_id: int,
    review_data: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.customer_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    update_data = review_data.dict(exclude_unset=True)
    await db.execute(
        update(Review).where(Review.id == review_id).values(**update_data)
    )
    await db.commit()
    return await db.get(Review, review_id)

@router.delete("/{review_id}", status_code=204)
async def delete_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.customer_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.execute(delete(Review).where(Review.id == review_id))
    await db.commit()
    return None