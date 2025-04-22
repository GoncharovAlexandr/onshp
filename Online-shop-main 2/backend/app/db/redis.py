import redis.asyncio as redis
import json
import os
from fastapi import Depends

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
POPULAR_KEY = "popular_products"

# Глобальное подключение к Redis
pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
redis_client = redis.Redis(connection_pool=pool)
from fastapi import Depends
from redis.asyncio import Redis
import json
import logging
logger = logging.getLogger(__name__)

async def get_redis() -> Redis:
    redis = Redis.from_url("redis://localhost:6379/0", decode_responses=True)
    try:
        yield redis
    finally:
        await redis.close()

async def init_redis():
    global redis_client
    try:
        await redis_client.ping()  # Проверка соединения
    except Exception as e:
        raise Exception(f"Failed to connect to Redis: {str(e)}")

async def close_redis():
    global redis_client
    await redis_client.aclose()
    await pool.disconnect()

async def get_redis() -> redis.Redis:
    return redis_client

async def add_popular_product(product_id: int, redis: Redis):
    try:
        await redis.zincrby("popular_products", 1, str(product_id))
        logger.debug(f"Incremented popularity for product {product_id}")
    except Exception as e:
        logger.error(f"Redis error in add_popular_product: {str(e)}")
        raise


async def get_popular_products(limit: int = 10, redis_client: redis.Redis = Depends(get_redis)):
    return await redis_client.zrevrange(POPULAR_KEY, 0, limit - 1)

async def set_cart(customer_id: int, cart_data: dict, redis_client: redis.Redis = Depends(get_redis)):
    key = f"cart:{customer_id}"
    await redis_client.set(key, json.dumps(cart_data))

async def get_cart(customer_id: int, redis_client: redis.Redis = Depends(get_redis)) -> dict | None:
    key = f"cart:{customer_id}"
    value = await redis_client.get(key)
    return json.loads(value) if value else None

async def clear_cart(customer_id: int, redis_client: redis.Redis = Depends(get_redis)):
    key = f"cart:{customer_id}"
    await redis_client.delete(key)

async def cache_product(product_id: int, product_data: dict, ttl: int = 300, redis_client: redis.Redis = Depends(get_redis)):
    key = f"product_cache:{product_id}"
    await redis_client.set(key, json.dumps(product_data), ex=ttl)

async def get_cached_product(product_id: int, redis_client: redis.Redis = Depends(get_redis)) -> dict | None:
    key = f"product_cache:{product_id}"
    value = await redis_client.get(key)
    return json.loads(value) if value else None

async def cache_order(order_id: int, order_data: dict, ttl: int = 300, redis_client: redis.Redis = Depends(get_redis)):
    key = f"order_cache:{order_id}"
    await redis_client.set(key, json.dumps(order_data), ex=ttl)

async def get_cached_order(order_id: int, redis_client: redis.Redis = Depends(get_redis)) -> dict | None:
    key = f"order_cache:{order_id}"
    value = await redis_client.get(key)
    return json.loads(value) if value else None