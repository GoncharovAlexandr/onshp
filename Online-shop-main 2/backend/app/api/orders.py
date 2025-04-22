from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from backend.app.db.postgres import get_db
from backend.app.models.postgres_models import Order, OrderItem, Product
from backend.app.schemas.order import OrderCreate, OrderOut
from backend.app.dependencies.auth import get_current_user
from backend.app.db.mongo import get_mongo_db, get_cart, clear_cart

router = APIRouter()
templates = Jinja2Templates(directory="templates")


async def get_auth_context(request: Request):
    is_authenticated = False
    session_id = request.cookies.get("session_id")
    if session_id:
        is_authenticated = True
    return {"request": request, "is_authenticated": is_authenticated}


@router.get("/html")
async def get_orders_html(context: dict = Depends(get_auth_context), user=Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.customer_id == user["id"]))
    orders = result.scalars().all()
    return templates.TemplateResponse("orders.html", {**context, "orders": orders})


@router.get("/{order_id}")
async def get_order_html(order_id: int, context: dict = Depends(get_auth_context), user=Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.customer_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    result = await db.execute(select(OrderItem).where(OrderItem.order_id == order_id))
    items = result.scalars().all()
    order_items = []
    for item in items:
        product = await db.get(Product, item.product_id)
        order_items.append({"item": item, "product": product})
    return templates.TemplateResponse("order_detail.html", {**context, "order": order, "order_items": order_items})


@router.get("/", response_model=List[OrderOut])
async def get_orders(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.customer_id == user["id"]))
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: int, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.customer_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return order


@router.post("/", response_model=OrderOut, status_code=201)
async def create_order(user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
                       db_mongo=Depends(get_mongo_db)):
    cart = await get_cart(db_mongo, str(user["id"]))
    if not cart or not cart.get("items"):
        raise HTTPException(status_code=400, detail="Cart is empty")

    order = Order(customer_id=user["id"], status="pending")
    db.add(order)
    await db.commit()
    await db.refresh(order)

    total_amount = 0
    for item in cart["items"]:
        product = await db.get(Product, item["product_id"])
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item['product_id']} not found")
        if product.stock_quantity < item["quantity"]:
            raise HTTPException(status_code=400, detail=f"Not enough stock for product {product.name}")
        order_item = OrderItem(
            order_id=order.id,
            product_id=item["product_id"],
            quantity=item["quantity"],
            price=product.price
        )
        db.add(order_item)
        product.stock_quantity -= item["quantity"]
        total_amount += product.price * item["quantity"]

    order.total_amount = total_amount
    await db.commit()
    await clear_cart(db_mongo, str(user["id"]))
    return RedirectResponse(url="/orders/html", status_code=303)