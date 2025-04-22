from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.app.db.postgres import init_db, get_db
from backend.app.db.redis import init_redis, close_redis
from backend.app.api import products, auth_user, auth_admin, categories, orders, reviews, order_items, user_profile, cart, promotions
from backend.app.models.postgres_models import Product

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить доступ с любых доменов
    allow_credentials=True,  # Разрешить передачу куки и других учетных данных
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем роутеры
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(auth_user.router, prefix="/user/auth", tags=["UserAuth"])
app.include_router(auth_admin.router, prefix="/user/auth/admin")
app.include_router(categories.router, prefix="/categories", tags=["Categories"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
app.include_router(order_items.router, prefix="/order-items", tags=["OrderItems"])
app.include_router(user_profile.router, prefix="/user/me", tags=["User Profile"])
app.include_router(cart.router, prefix="/cart", tags=["Cart"])
app.include_router(promotions.router, prefix="/promotions", tags=["Promotions"])

@app.on_event("startup")
async def startup_event():
    await init_redis()
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    await close_redis()

@app.get("/")
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).limit(4))
    products = result.scalars().all()
    return templates.TemplateResponse("home.html", {"request": request, "products": products})
