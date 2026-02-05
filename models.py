# models.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    DateTime,
    String,
    ForeignKey,
    UniqueConstraint,
    Index,
    Enum,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, TINYINT


class Base(DeclarativeBase):
    pass

# users
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    wishlist: Mapped[List["Wishlist"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# items
class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    external_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    product_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    mall_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    initial_price: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False)
    last_seen_price: Mapped[Optional[int]] = mapped_column(INTEGER(unsigned=True), nullable=True)
    min_price: Mapped[Optional[int]] = mapped_column(INTEGER(unsigned=True), nullable=True)

    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    is_active: Mapped[int] = mapped_column(
        TINYINT(1), nullable=False, server_default=text("1")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    wishlist: Mapped[List["Wishlist"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    price_history: Mapped[List["PriceHistory"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_items_active_checked", "is_active", "last_checked_at"),
        Index("ix_items_created_at", "created_at"),
    )


# wishlist (user <-> item)
class Wishlist(Base):
    __tablename__ = "wishlist"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    is_active: Mapped[int] = mapped_column(
        TINYINT(1), nullable=False, server_default=text("1")
    )

    user: Mapped["User"] = relationship(back_populates="wishlist")
    item: Mapped["Item"] = relationship(back_populates="wishlist")

    alerts: Mapped[List["Alert"]] = relationship(
        back_populates="wishlist",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_wishlist_user_item"),
        Index("ix_wishlist_user", "user_id"),
        Index("ix_wishlist_item", "item_id"),
    )


# price_history
class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    item_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
    )
    price: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    item: Mapped["Item"] = relationship(back_populates="price_history")

    __table_args__ = (
        Index("ix_ph_item_checked", "item_id", "checked_at"),
    )


# alerts
AlertTypeEnum = Enum("TARGET_PRICE", "DROP_FROM_PREV", "NEW_LOW", name="alert_type")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    wishlist_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("wishlist.id", ondelete="CASCADE"),
        nullable=False,
    )

    alert_type: Mapped[str] = mapped_column(AlertTypeEnum, nullable=False)
    target_price: Mapped[Optional[int]] = mapped_column(INTEGER(unsigned=True), nullable=True)

    is_enabled: Mapped[int] = mapped_column(
        TINYINT(1), nullable=False, server_default=text("1")
    )

    last_triggered_ph_id: Mapped[Optional[int]] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("price_history.id", ondelete="SET NULL"),
        nullable=True,
    )

    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    wishlist: Mapped["Wishlist"] = relationship(back_populates="alerts")
    last_triggered_ph: Mapped[Optional["PriceHistory"]] = relationship(
        foreign_keys=[last_triggered_ph_id],
        lazy="joined",
    )

    __table_args__ = (
        Index("ix_alerts_wishlist", "wishlist_id"),
        Index("ix_alerts_enabled_wishlist", "is_enabled", "wishlist_id"),
        Index("ix_alerts_last_ph", "last_triggered_ph_id"),
    )
