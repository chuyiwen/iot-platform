"""Generic async CRUD base class.

Callers are responsible for committing the session.  These methods never call
``db.commit()`` so that the calling layer (service, route handler, or test)
retains full control over transaction boundaries.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .base_model import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=PydanticBaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=PydanticBaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Async CRUD helper parameterised on a SQLAlchemy model and two Pydantic schemas."""

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get(self, db: AsyncSession, id: int) -> ModelType | None:
        """Return the record with the given *id*, or ``None`` if not found / deleted."""
        result = await db.execute(
            select(self.model).where(
                self.model.id == id,
                self.model.deleted.is_(False),
            )
        )
        return result.scalars().first()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        filters: dict[str, Any] | None = None,
        order_by: str = "id",
        order_desc: bool = True,
    ) -> tuple[list[ModelType], int]:
        """Return a paginated list of non-deleted records and the total count.

        Parameters
        ----------
        skip:      number of rows to skip (offset)
        limit:     maximum rows to return
        filters:   mapping of column-name → exact-match value
        order_by:  column name to sort by
        order_desc: descending when True, ascending when False
        """
        base_where = [self.model.deleted.is_(False)]

        if filters:
            for field, value in filters.items():
                col = getattr(self.model, field)
                base_where.append(col == value)

        # --- total count (no subquery: select_from the model table directly) ---
        count_stmt = select(func.count()).select_from(self.model).where(*base_where)
        total: int = (await db.execute(count_stmt)).scalar_one()

        # --- data query ---
        order_col = getattr(self.model, order_by)
        order_expr = order_col.desc() if order_desc else order_col.asc()

        data_stmt = (
            select(self.model)
            .where(*base_where)
            .order_by(order_expr)
            .offset(skip)
            .limit(limit)
        )
        items: list[ModelType] = list((await db.execute(data_stmt)).scalars().all())

        return items, total

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: CreateSchemaType,
        creator_id: int | None = None,
    ) -> ModelType:
        """Persist a new record and return the ORM instance (not yet committed)."""
        data = obj_in.model_dump(exclude_unset=True)
        data["creator_id"] = creator_id
        data["updater_id"] = creator_id
        db_obj = self.model(**data)
        db.add(db_obj)
        await db.flush()  # populate server defaults (id, created_at, …)
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
        updater_id: int | None = None,
    ) -> ModelType:
        """Apply *obj_in* to *db_obj* and return the updated instance (not committed)."""
        if isinstance(obj_in, PydanticBaseModel):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            update_data = dict(obj_in)

        update_data["updater_id"] = updater_id

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        id: int,
        updater_id: int | None = None,
    ) -> bool:
        """Mark the record as deleted.

        Returns ``True`` when the record was found, ``False`` when it did not exist
        or was already deleted.
        """
        db_obj = await self.get(db, id)
        if db_obj is None:
            return False

        db_obj.deleted = True  # type: ignore[assignment]
        db_obj.updater_id = updater_id  # type: ignore[assignment]
        db.add(db_obj)
        await db.flush()
        return True
