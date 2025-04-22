from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from backend.app.schemas.user_profile import UserProfileOut, UserProfileCreate
from backend.app.schemas.cart import CartItem, CartOut
import os
from bson import ObjectId

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB_NAME = "db"

client = MongoClient(MONGO_URL)
db = client[MONGO_DB_NAME]

products_collection: Collection = db["products"]
COLLECTION = "user_profiles"
CARTS_COLLECTION = "carts"
PROMO_COLLECTION = "promotions"

def get_mongo_db() -> Database:
    return db

def get_mongo_collection():
    return products_collection

def get_user_profile(db: Database, customer_id: str) -> UserProfileOut | None:
    doc = db[COLLECTION].find_one({"customer_id": customer_id})
    return UserProfileOut(**doc) if doc else None

def create_user_profile(db: Database, data: UserProfileCreate) -> UserProfileOut:
    db[COLLECTION].insert_one(data.dict())
    return get_user_profile(db, data.customer_id)

def update_user_profile(db: Database, customer_id: str, update_data: dict) -> UserProfileOut:
    db[COLLECTION].update_one({"customer_id": customer_id}, {"$set": update_data})
    return get_user_profile(db, customer_id)

def push_to_list(db: Database, customer_id: str, field: str, value: int):
    db[COLLECTION].update_one({"customer_id": customer_id}, {"$addToSet": {field: value}})

def remove_from_list(db: Database, customer_id: str, field: str, value: int):
    db[COLLECTION].update_one({"customer_id": customer_id}, {"$pull": {field: value}})

def get_cart(db: Database, user_id: str) -> dict:
    cart = db[CARTS_COLLECTION].find_one({"user_id": user_id})
    return cart if cart else {"items": [], "user_id": user_id}

def add_to_cart(db: Database, customer_id: str, item: dict):
    cart = get_cart(db, customer_id)
    for existing in cart["items"]:
        if existing["product_id"] == item["product_id"]:
            existing["quantity"] += item["quantity"]
            break
    else:
        cart["items"].append(item)
    db[CARTS_COLLECTION].update_one(
        {"customer_id": customer_id},
        {"$set": {"items": cart["items"]}},
        upsert=True
    )

def remove_from_cart(db: Database, customer_id: str, product_id: int):
    cart = get_cart(db, customer_id)
    cart["items"] = [item for item in cart["items"] if item["product_id"] != product_id]
    db[CARTS_COLLECTION].update_one(
        {"customer_id": customer_id},
        {"$set": {"items": cart["items"]}},
        upsert=True
    )

def clear_cart(db: Database, customer_id: str):
    db[CARTS_COLLECTION].update_one(
        {"customer_id": customer_id},
        {"$set": {"items": []}},
        upsert=True
    )

def set_cart(customer_id: str, cart: dict, db: Database):
    db[CARTS_COLLECTION].update_one(
        {"customer_id": customer_id},
        {"$set": cart},
        upsert=True
    )

def get_all_promotions(db: Database):
    cursor = db[PROMO_COLLECTION].find()
    return [format_promotion(doc) for doc in cursor]

def get_promotion(db: Database, promo_id: str):
    doc = db[PROMO_COLLECTION].find_one({"_id": ObjectId(promo_id)})
    return format_promotion(doc) if doc else None

def create_promotion(db: Database, data: dict):
    result = db[PROMO_COLLECTION].insert_one(data)
    return get_promotion(db, str(result.inserted_id))

def delete_promotion(db: Database, promo_id: str):
    db[PROMO_COLLECTION].delete_one({"_id": ObjectId(promo_id)})

def format_promotion(doc):
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "description": doc["description"],
        "discount": doc["discount"],
        "products": doc.get("products", [])
    }

def get_promotions_by_product_id(db: Database, product_id: int) -> list[dict]:
    cursor = db[PROMO_COLLECTION].find({"products": product_id})
    return [format_promotion(doc) for doc in cursor]


