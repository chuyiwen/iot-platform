# SQLAlchemy ORM abstract base for multi-tenant models.
from sqlalchemy.orm import Mapped, mapped_column

from .base_model import BaseModel, _BigInt


class TenantModel(BaseModel):
    """Abstract base that adds a tenant_id column to every multi-tenant table."""

    __abstract__ = True

    tenant_id: Mapped[int] = mapped_column(_BigInt, nullable=False, index=True)
