from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, index=True)
    unit_price = Column(Float, nullable=False)
    unit = Column(String, default="each")  # e.g. "L", "kg", "each"
    nutrition_tags = Column(String, default="")  # comma-separated, simple for MVP
    embedding_id = Column(Integer, nullable=True)  # FK into vector store metadata

    price_history = relationship("PriceHistory", back_populates="product")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    price = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="price_history")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float, default=1.0)
    purchased_at = Column(DateTime, default=datetime.utcnow)
