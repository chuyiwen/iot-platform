# SQLAlchemy ORM base classes — NOT related to Pydantic schemas.
# All application models should inherit from BaseModel (or TenantModel).
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# BigInteger that degrades gracefully to INTEGER on SQLite (required for
# autoincrement primary keys; PostgreSQL always sees BIGINT).
_BigInt = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    """Root declarative base shared by all ORM models in this application."""


class BaseModel(Base):
    """Abstract base model with audit fields and soft-delete support.

    Fields
    ------
    id          : surrogate primary key (auto-increment BigInteger)
    created_at  : row insertion timestamp (server-side default)
    updated_at  : last-update timestamp (server-side default, updated on change)
    creator_id  : BigInteger FK-hint to the user who created the record (nullable)
    updater_id  : BigInteger FK-hint to the user who last updated the record (nullable)
    deleted     : soft-delete flag; rows with deleted=True are treated as removed
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(_BigInt, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    creator_id: Mapped[int | None] = mapped_column(_BigInt, nullable=True)
    updater_id: Mapped[int | None] = mapped_column(_BigInt, nullable=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
