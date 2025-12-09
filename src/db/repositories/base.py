"""Base repository with common CRUD operations."""

from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Base

# Type variable for ORM models
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository[ModelType: Base]:
    """Base repository providing common database operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession):
        """
        Initialize base repository.

        Args:
            model: SQLAlchemy ORM model class
            session: Database session
        """
        self.model = model
        self.session = session

    async def create(self, **kwargs: Any) -> ModelType:
        """
        Create a new record.

        Args:
            **kwargs: Model field values

        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get_by_id(self, id: UUID) -> ModelType | None:
        """
        Get record by ID.

        Args:
            id: Record UUID

        Returns:
            Model instance or None if not found
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalars().first()

    async def get_or_404(self, id: UUID) -> ModelType:
        """
        Get record by ID or raise exception.

        Args:
            id: Record UUID

        Returns:
            Model instance

        Raises:
            ValueError: If record not found
        """
        instance = await self.get_by_id(id)
        if instance is None:
            raise ValueError(f"{self.model.__name__} with id {id} not found")
        return instance

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        **filters: Any
    ) -> list[ModelType]:
        """
        List records with pagination and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field name to order by (prefix with '-' for DESC)
            **filters: Field=value filters

        Returns:
            List of model instances
        """
        query = select(self.model)

        # Apply filters
        for field, value in filters.items():
            if value is not None:
                query = query.where(getattr(self.model, field) == value)

        # Apply ordering
        if order_by:
            if order_by.startswith("-"):
                field = order_by[1:]
                query = query.order_by(getattr(self.model, field).desc())
            else:
                query = query.order_by(getattr(self.model, order_by))
        else:
            # Default ordering by created_at if available
            if hasattr(self.model, "created_at"):
                query = query.order_by(self.model.created_at.desc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, **filters: Any) -> int:
        """
        Count records matching filters.

        Args:
            **filters: Field=value filters

        Returns:
            Count of matching records
        """
        query = select(func.count()).select_from(self.model)

        # Apply filters
        for field, value in filters.items():
            if value is not None:
                query = query.where(getattr(self.model, field) == value)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def update(self, id: UUID, **kwargs: Any) -> ModelType | None:
        """
        Update record by ID.

        Args:
            id: Record UUID
            **kwargs: Fields to update

        Returns:
            Updated model instance or None if not found
        """
        instance = await self.get_by_id(id)
        if instance is None:
            return None

        for field, value in kwargs.items():
            if value is not None and hasattr(instance, field):
                setattr(instance, field, value)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: UUID) -> bool:
        """
        Delete record by ID.

        Args:
            id: Record UUID

        Returns:
            True if deleted, False if not found
        """
        instance = await self.get_by_id(id)
        if instance is None:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def exists(self, id: UUID) -> bool:
        """
        Check if record exists.

        Args:
            id: Record UUID

        Returns:
            True if exists, False otherwise
        """
        result = await self.session.execute(
            select(func.count()).select_from(self.model).where(self.model.id == id)
        )
        return result.scalar_one() > 0

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[ModelType]:
        """
        Create multiple records in bulk.

        Args:
            items: List of dictionaries with field values

        Returns:
            List of created model instances
        """
        instances = [self.model(**item) for item in items]
        self.session.add_all(instances)
        await self.session.flush()
        for instance in instances:
            await self.session.refresh(instance)
        return instances
