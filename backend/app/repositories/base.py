"""Generic CRUD base for repositories.

Most repositories repeat the same four operations:

* fetch a single row by primary key (UUID),
* persist a new ORM instance,
* apply a ``dict`` of changes to an existing instance,
* delete an instance.

Centralising those operations here keeps the per-resource repositories
focused on the queries that actually differ — ``get_all`` (ordering and
filtering vary), ``get_by_name``/``get_by_path``/``get_by_endpoint_id``
(different lookup columns), and bespoke retention queries on
``snapshot`` / ``job_run``.

Repositories that need any of the standard four operations should
inherit ``BaseCrudRepository`` and set ``model`` to their SQLAlchemy
ORM class. Inheritance is explicitly *additive*: subclasses keep
defining their custom queries; the base only fills in the boilerplate.
"""

from __future__ import annotations

import uuid
from typing import ClassVar, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseCrudRepository(Generic[ModelT]):
    """Shared CRUD operations keyed on a UUID primary key.

    Subclasses must set the ``model`` class variable to the ORM class
    they wrap. Example::

        class ConnectionRepository(BaseCrudRepository[OracleConnection]):
            model = OracleConnection

            async def get_all(self, *, active_only=False): ...
    """

    model: ClassVar[type[Base]]

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, obj_id: uuid.UUID) -> ModelT | None:
        result = await self._db.execute(
            select(self.model).where(self.model.id == obj_id)  # type: ignore[attr-defined]
        )
        # ``self.model`` is a ``ClassVar[type[Base]]`` so mypy widens the
        # row type to ``Base | None``; the runtime type matches ``ModelT``
        # because subclasses set ``model`` to their own ORM class.
        return result.scalar_one_or_none()  # type: ignore[return-value]

    async def create(self, obj: ModelT) -> ModelT:
        self._db.add(obj)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def update(self, obj: ModelT, changes: dict[str, object]) -> ModelT:
        for field, value in changes.items():
            setattr(obj, field, value)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self._db.delete(obj)
        await self._db.flush()
