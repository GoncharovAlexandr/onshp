from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile, File, status, Cookie
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List
from backend.app.models.postgres_models import Product, Category, Review
from backend.app.db.postgres import get_db
from backend.app.db.mongo import get_mongo_collection
from backend.app.dependencies.auth import get_current_admin
from backend.app.db.redis import get_redis, get_cached_product, cache_product, add_popular_product, get_popular_products
import json
import os
import logging

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def get_auth_context(request: Request, session_id: str = Cookie(default=None), redis: Redis = Depends(get_redis)):
    is_authenticated = False
    is_admin = False
    logger.debug(f"Checking auth context with session_id: {session_id}")
    if session_id:
        session_data = await redis.get(f"session:{session_id}")
        if session_data:
            try:
                session = json.loads(session_data)
                is_authenticated = True
                is_admin = "admin_id" in session
                logger.debug(f"Auth context: session_id={session_id}, is_authenticated={is_authenticated}, is_admin={is_admin}, session_data={session}")
            except json.JSONDecodeError:
                logger.error("Failed to decode session data")
    else:
        logger.debug("No session_id provided in auth context")
    return {"request": request, "is_authenticated": is_authenticated, "user": {"is_admin": is_admin}}

@router.get("/html")
async def get_products_html(context: dict = Depends(get_auth_context), db: AsyncSession = Depends(get_db)):
    query = context["request"].query_params.get("query", "")
    stmt = select(Product)
    if query:
        stmt = stmt.where(Product.name.ilike(f"%{query}%"))
    try:
        result = await db.execute(stmt)
        products = result.scalars().all()
        await db.commit()
        logger.debug(f"Fetched {len(products)} products")
    except Exception as e:
        logger.error(f"Database error in get_products_html: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch products: {str(e)}")
    return templates.TemplateResponse("products.html", {**context, "products": products, "query": query})

@router.get("/new")
async def create_product_form(context: dict = Depends(get_auth_context), db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    try:
        result = await db.execute(select(Category))
        categories = result.scalars().all()
        await db.commit()
        logger.debug(f"Fetched {len(categories)} categories for product form")
    except Exception as e:
        logger.error(f"Database error in create_product_form: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch categories: {str(e)}")
    return templates.TemplateResponse("product_form.html", {**context, "categories": categories, "title": "Создать товар", "action": "/products/new", "button_text": "Создать"})

@router.post("/new")
async def create_product_html(
    name: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    stock_quantity: int = Form(...),
    description: str = Form(default=None),
    image: UploadFile = File(default=None),
    db: AsyncSession = Depends(get_db),
    mongo=Depends(get_mongo_collection),
    admin=Depends(get_current_admin)
):
    try:
        category = await db.get(Category, category_id)
        if not category:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found")
        image_path = None
        if image:
            image_path = f"static/images/{image.filename}"
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            with open(image_path, "wb") as f:
                f.write(await image.read())
        product = Product(
            name=name,
            price=price,
            category_id=category_id,
            stock_quantity=stock_quantity,
            image=image_path
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
        async with get_mongo_collection() as mongo:
            mongo["products"].insert_one({
                "product_id": product.id,
                "description": description or "",
                "attributes": {}
            })
        logger.debug(f"Created product: {product.id}, name: {name}")
    except Exception as e:
        logger.error(f"Database error in create_product_html: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create product: {str(e)}")
    return RedirectResponse(url=f"/products/{product.id}", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/{product_id}")
async def get_product_html(product_id: int, context: dict = Depends(get_auth_context), db: AsyncSession = Depends(get_db), redis=Depends(get_redis)):
    try:
        product = await db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        result = await db.execute(select(Review).where(Review.product_id == product_id))
        reviews = result.scalars().all()
        avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else 0
        await add_popular_product(product_id, redis)
        await db.commit()
        logger.debug(f"Fetched product: {product_id}, reviews: {len(reviews)}")
    except Exception as e:
        logger.error(f"Database error in get_product_html: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch product: {str(e)}")
    return templates.TemplateResponse("product_detail.html", {**context, "product": product, "reviews": reviews, "avg_rating": avg_rating})

@router.get("/edit/{product_id}")
async def edit_product_form(product_id: int, context: dict = Depends(get_auth_context), db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    try:
        product = await db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        result = await db.execute(select(Category))
        categories = result.scalars().all()
        await db.commit()
        logger.debug(f"Fetched product for edit: {product_id}, categories: {len(categories)}")
    except Exception as e:
        logger.error(f"Database error in edit_product_form: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch product or categories: {str(e)}")
    return templates.TemplateResponse("product_form.html", {**context, "product": product, "categories": categories, "title": "Редактировать товар", "action": f"/products/edit/{product_id}", "button_text": "Сохранить"})

@router.post("/edit/{product_id}")
async def edit_product(
    product_id: int,
    name: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    stock_quantity: int = Form(...),
    description: str = Form(default=None),
    image: UploadFile = File(default=None),
    db: AsyncSession = Depends(get_db),
    mongo=Depends(get_mongo_collection),
    admin=Depends(get_current_admin)
):
    try:
        product = await db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        update_data = {
            "name": name,
            "price": price,
            "category_id": category_id,
            "stock_quantity": stock_quantity
        }
        if image:
            image_path = f"static/images/{image.filename}"
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            with open(image_path, "wb") as f:
                f.write(await image.read())
            update_data["image"] = image_path
        await db.execute(update(Product).where(Product.id == product_id).values(**update_data))
        await db.commit()
        async with get_mongo_collection() as mongo:
            mongo["products"].update_one(
                {"product_id": product_id},
                {"$set": {"description": description or "", "attributes": {}}},
                upsert=True
            )
        logger.debug(f"Edited product: {product_id}, name: {name}")
    except Exception as e:
        logger.error(f"Database error in edit_product: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to edit product: {str(e)}")
    return RedirectResponse(url=f"/products/{product_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/delete/{product_id}")
async def delete_product_html(product_id: int, db: AsyncSession = Depends(get_db), mongo=Depends(get_mongo_collection), admin=Depends(get_current_admin)):
    try:
        product = await db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        await db.execute(delete(Product).where(Product.id == product_id))
        await db.commit()
        async with get_mongo_collection() as mongo:
            mongo["products"].delete_one({"product_id": product_id})
        logger.debug(f"Deleted product: {product_id}")
    except Exception as e:
        logger.error(f"Database error in delete_product_html: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete product: {str(e)}")
    return RedirectResponse(url="/products/html", status_code=status.HTTP_303_SEE_OTHER)