from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List, Optional
import logging

from backend.app.db.postgres import get_db
from backend.app.db.redis import get_redis
from backend.app.models.postgres_models import Category
from backend.app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from backend.app.dependencies.auth import get_current_admin

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

async def get_auth_context(request: Request, redis=Depends(get_redis)):
    is_authenticated = False
    session_id = request.cookies.get("session_id")
    if session_id:
        session_data = await redis.get(f"session:{session_id}")
        if session_data:
            is_authenticated = True
    return {"request": request, "is_authenticated": is_authenticated}

@router.get("/html")
async def get_categories_html(
    request: Request,
    query: str = "",
    context: dict = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Category)
    if query:
        stmt = stmt.filter(Category.name.ilike(f"%{query}%"))
    result = await db.execute(stmt)
    categories = result.scalars().all()
    return templates.TemplateResponse(
        "categories.html",
        {**context, "categories": categories, "query": query}
    )

@router.get("/create")
async def get_create_category_form(context: dict = Depends(get_auth_context), admin=Depends(get_current_admin)):
    return templates.TemplateResponse("category_create.html", context)

@router.get("/edit/{category_id}")
async def get_edit_category_form(
    category_id: int,
    context: dict = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    category = await db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return templates.TemplateResponse("category_edit.html", {**context, "category": category})

@router.get("/", response_model=List[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category))
    return result.scalars().all()

@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    category = await db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(
    name: str = Form(...),
    description: Optional[str] = Form(""),
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    logger.info(f"Creating category: name={name}, description={description}")
    try:
        category_data = CategoryCreate(name=name, description=description if description else None)
        category = Category(**category_data.model_dump())
        db.add(category)
        await db.commit()
        await db.refresh(category)
        logger.info(f"Category created: id={category.id}, description={category.description}")
        return RedirectResponse(url="/categories/html", status_code=303)
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating category: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Ошибка при создании категории: {str(e)}")

@router.post("/{category_id}", response_model=CategoryResponse)
async def update_category_form(
    category_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(""),
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    logger.info(f"Updating category: id={category_id}, name={name}, description={description}")
    category = await db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    update_data = {"name": name, "description": description if description else None}
    await db.execute(
        update(Category)
        .where(Category.id == category_id)
        .values(**update_data)
    )
    await db.commit()
    await db.refresh(category)
    logger.info(f"Category updated: id={category_id}, description={category.description}")
    return RedirectResponse(url="/categories/html", status_code=303)

@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    category = await db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    update_data = category_data.model_dump(exclude_unset=True)
    await db.execute(
        update(Category)
        .where(Category.id == category_id)
        .values(**update_data)
    )
    await db.commit()
    await db.refresh(category)
    return category

@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    category = await db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.execute(delete(Category).where(Category.id == category_id))
    await db.commit()
    return None