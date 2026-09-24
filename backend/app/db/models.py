from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    purchases = relationship("Purchase", back_populates="user")
    baskets = relationship("Basket", back_populates="user")


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    price_observations = relationship(
        "PriceObservation",
        back_populates="store",
    )


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    brand = Column(String, nullable=True)
    category = Column(String, index=True)
    sub_category = Column(String, nullable=True, index=True)
    product_group = Column(String, nullable=True)
    barcode = Column(String, nullable=True, index=True)
    package_size = Column(String, nullable=True)

    # Temporary compatibility field.
    # New pricing should come from PriceObservation.
    unit_price = Column(Float, nullable=False)
    unit = Column(String, default="each")
    nutrition_tags = Column(String, default="")
    embedding_id = Column(Integer, nullable=True)

    source = Column(String, nullable=True, index=True)
    source_product_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    price_history = relationship(
        "PriceHistory",
        back_populates="product",
    )
    price_observations = relationship(
        "PriceObservation",
        back_populates="product",
    )
    purchases = relationship(
        "Purchase",
        back_populates="product",
    )


class PriceObservation(Base):
    """A market price observed for a product at a store and point in time."""

    __tablename__ = "price_observations"

    id = Column(Integer, primary_key=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        index=True,
    )

    store_id = Column(
        Integer,
        ForeignKey("stores.id"),
        nullable=True,
        index=True,
    )

    # Location belongs to the observation because the same product
    # can have different observed prices across Australian markets.
    postal_code = Column(String, nullable=True, index=True)
    state = Column(String, nullable=True, index=True)
    city = Column(String, nullable=True, index=True)

    price = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(10, 4), nullable=True)
    unit_price_unit = Column(String, nullable=True)
    retail_price = Column(Numeric(10, 2), nullable=True)

    is_special = Column(Boolean, nullable=False, default=False)
    in_stock = Column(Boolean, nullable=True)
    is_estimated = Column(Boolean, nullable=True)

    observed_at = Column(DateTime, nullable=False, index=True)

    source = Column(String, nullable=False, index=True)
    source_record_id = Column(String, nullable=True, index=True)
    source_url = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    product = relationship(
        "Product",
        back_populates="price_observations",
    )

    store = relationship(
        "Store",
        back_populates="price_observations",
    )


class PriceHistory(Base):
    """Legacy compatibility model retained while forecasting is migrated."""

    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
    )

    price = Column(Float, nullable=False)

    recorded_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    product = relationship(
        "Product",
        back_populates="price_history",
    )


class Basket(Base):
    __tablename__ = "baskets"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # External basket identifier from the source dataset.
    source_basket_id = Column(
        String,
        nullable=False,
        index=True,
    )

    store_id = Column(
        Integer,
        ForeignKey("stores.id"),
        nullable=True,
        index=True,
    )

    purchased_at = Column(
        DateTime,
        nullable=False,
        index=True,
    )

    user = relationship(
        "User",
        back_populates="baskets",
    )

    store = relationship("Store")

    purchases = relationship(
        "Purchase",
        back_populates="basket",
    )


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        index=True,
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
    )

    basket_id = Column(
        Integer,
        ForeignKey("baskets.id"),
        nullable=True,
        index=True,
    )

    quantity = Column(
        Float,
        default=1.0,
    )

    # Raw transaction-level financial facts from the source dataset.
    # Nullable because older synthetic purchases do not contain these values.
    sales_value = Column(
        Numeric(12, 4),
        nullable=True,
    )

    retail_discount = Column(
        Numeric(12, 4),
        nullable=True,
    )

    coupon_discount = Column(
        Numeric(12, 4),
        nullable=True,
    )

    coupon_match_discount = Column(
        Numeric(12, 4),
        nullable=True,
    )

    purchased_at = Column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )

    user = relationship(
        "User",
        back_populates="purchases",
    )

    product = relationship(
        "Product",
        back_populates="purchases",
    )

    basket = relationship(
        "Basket",
        back_populates="purchases",
    )