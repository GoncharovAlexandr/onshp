from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy import Numeric as Decimal
from sqlalchemy.orm import relationship
from backend.app.db.postgres import Base
from datetime import datetime

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    products = relationship("Product", back_populates="category")

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'))
    order_date = Column(DateTime, nullable=False)
    total_amount = Column(Decimal(10, 2), nullable=False)
    status = Column(String(50), default='pending')
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = 'order_items'
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, nullable=False)
    price = Column(Decimal(10, 2), nullable=False)
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    price = Column(Decimal(10, 2), nullable=False)
    stock_quantity = Column(Integer, default=0)
    image = Column(String(255))
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    reviews = relationship("Review", back_populates="product")

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    phone = Column(String(20))
    address = Column(Text)
    orders = relationship("Order", back_populates="customer")
    reviews = relationship("Review", back_populates="customer")

class Review(Base):
    __tablename__ = 'reviews'
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    customer_id = Column(Integer, ForeignKey('customers.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    product = relationship("Product", back_populates="reviews")
    customer = relationship("Customer", back_populates="reviews")

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)