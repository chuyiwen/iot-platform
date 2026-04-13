# SQLAlchemy ORM abstract base for multi-tenant models.
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from .base_model import BaseModel


class TenantModel(BaseModel):
    """Abstract base that adds a tenant_id column to every multi-tenant table."""

    __abstract__ = True

    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
