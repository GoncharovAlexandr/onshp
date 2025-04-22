import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.app.db.mongo import get_mongo_db, get_cart, add_to_cart, remove_from_cart, clear_cart, set_cart
from backend.app.db.postgres import get_db
from backend.app.db.redis import get_redis
from backend.app.models.postgres_models import Product
from backend.app.dependencies.auth import get_current_user
from backend.app.schemas.cart import CartItem, CartOut
import json

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

async def get_auth_context(request: Request, redis=Depends(get_redis)):
    logger.debug("Getting auth context")
    is_authenticated = False
    session_id = request.cookies.get("session_id")
    if session_id:
        session_data = await redis.get(f"session:{session_id}")
        if session_data:
            is_authenticated = True
    return {"request": request, "is_authenticated": is_authenticated}

@router.get("/html")
async def read_cart_html(context: dict = Depends(get_auth_context), user=Depends(get_current_user), db_pg: AsyncSession = Depends(get_db), db_mongo=Depends(get_mongo_db)):
    logger.debug(f"Reading cart for user: {user}")
    cart = get_cart(db_mongo, str(user["customer_id"]))
    if not cart or not cart.get("items"):
        return templates.TemplateResponse("cart.html", {**context, "cart_items": [], "total": 0})

    product_ids = [item["product_id"] for item in cart["items"]]
    result = await db_pg.execute(select(Product).where(Product.id.in_(product_ids)))
    products = {p.id: p for p in result.scalars().all()}

    cart_items = []
    total = 0
    for item in cart["items"]:
        product = products.get(item["product_id"])
        if product:
            cart_items.append({
                "product": product,
                "quantity": item["quantity"]
            })
            total += product.price * item["quantity"]

    return templates.TemplateResponse("cart.html", {**context, "cart_items": cart_items, "total": total})

@router.get("/", response_model=CartOut)
async def read_cart(user=Depends(get_current_user), db=Depends(get_mongo_db)):
    logger.debug(f"Reading cart API for user: {user}")
    cart = get_cart(db, str(user["customer_id"]))
    if not cart or not cart.get("items"):
        raise HTTPException(status_code=404, detail="Cart is empty")
    return cart

@router.post("/add", status_code=201)
async def add_to_cart_endpoint(item: CartItem, user=Depends(get_current_user), db_mongo=Depends(get_mongo_db)):
    logger.debug(f"Adding to cart (endpoint): {item}, user: {user}")
    cart = get_cart(db_mongo, str(user["customer_id"])) or {"items": [], "customer_id": str(user["customer_id"])}
    for existing in cart["items"]:
        if existing["product_id"] == item.product_id:
            existing["quantity"] += item.quantity
            break
    else:
        cart["items"].append(item.dict())
    set_cart(str(user["customer_id"]), cart, db_mongo)
    return cart

@router.post("/add/html")
async def add_to_cart_html(
    product_id: int = Form(...),
    quantity: int = Form(...),
    user=Depends(get_current_user),
    db_mongo=Depends(get_mongo_db),
    db_pg: AsyncSession = Depends(get_db)
):
    logger.debug(f"Adding to cart (html): product_id={product_id}, quantity={quantity}, user={user}")
    product = await db_pg.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if quantity > product.stock_quantity:
        raise HTTPException(status_code=400, detail="Requested quantity exceeds stock")
    cart = get_cart(db_mongo, str(user["customer_id"])) or {"items": [], "customer_id": str(user["customer_id"])}
    for existing in cart["items"]:
        if existing["product_id"] == product_id:
            existing["quantity"] += quantity
            break
    else:
        cart["items"].append({"product_id": product_id, "quantity": quantity})
    set_cart(str(user["customer_id"]), cart, db_mongo)
    return RedirectResponse(url="/cart/html", status_code=303)

@router.post("/add/{product_id}")
async def add_to_cart_by_id(
    product_id: int,
    quantity: int = 1,  # По умолчанию добавляем 1 единицу товара
    user=Depends(get_current_user),
    db_mongo=Depends(get_mongo_db),
    db_pg: AsyncSession = Depends(get_db)
):
    logger.debug(f"Adding to cart by ID: product_id={product_id}, quantity={quantity}, user={user}")
    # Проверяем, существует ли продукт
    product = await db_pg.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if quantity > product.stock_quantity:
        raise HTTPException(status_code=400, detail="Requested quantity exceeds stock")

    # Получаем корзину или создаем пустую
    cart = get_cart(db_mongo, str(user["customer_id"])) or {"items": [], "customer_id": str(user["customer_id"])}

    # Обновляем или добавляем товар в корзину
    for existing in cart["items"]:
        if existing["product_id"] == product_id:
            existing["quantity"] += quantity
            break
    else:
        cart["items"].append({"product_id": product_id, "quantity": quantity})

    # Сохраняем корзину
    set_cart(str(user["customer_id"]), cart, db_mongo)
    return RedirectResponse(url="/cart/html", status_code=303)

@router.post("/remove", status_code=204)
async def remove_item(item: CartItem, user=Depends(get_current_user), db=Depends(get_mongo_db)):
    logger.debug(f"Removing item: {item}, user={user}")
    remove_from_cart(db, str(user["customer_id"]), item.product_id)
    return {"message": "Item removed"}

@router.post("/remove/html")
async def remove_item_html(
    product_id: int = Form(...),
    user=Depends(get_current_user),
    db=Depends(get_mongo_db)
):
    logger.debug(f"Removing item (html): product_id={product_id}, user={user}")
    remove_from_cart(db, str(user["customer_id"]), product_id)
    return RedirectResponse(url="/cart/html", status_code=303)

@router.post("/clear", status_code=204)
async def clear(user=Depends(get_current_user), db=Depends(get_mongo_db)):
    logger.debug(f"Clearing cart for user: {user}")
    clear_cart(db, str(user["customer_id"]))
    return {"message": "Cart cleared"}