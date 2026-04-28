"""Tests for ``BaseCrudRepository``.

The repositories that inherit it (``connection``, ``endpoint``,
``auth_method``, ``schedule``, ``job_run``) already exercise the
inherited methods indirectly through router-level integration tests,
but pinning the contract directly here makes it easier to spot
regressions if the base class changes.
"""

import uuid

import pytest
from app.models.connection import OracleConnection
from app.repositories.base import BaseCrudRepository
from app.repositories.connection import ConnectionRepository
from sqlalchemy.ext.asyncio import AsyncSession


def _make_connection(name: str = "base-repo-test") -> OracleConnection:
    return OracleConnection(
        name=name,
        host="oracle.example.com",
        service_name="ORCLPDB",
        username="hr",
        encrypted_password=b"x",
        is_active=True,
    )


async def test_create_persists_and_returns_object_with_id(
    db_session: AsyncSession,
) -> None:
    repo = ConnectionRepository(db_session)
    obj = await repo.create(_make_connection("create-1"))
    assert obj.id is not None
    # ``create`` flushed; the row is visible via a fresh ``get_by_id``.
    fetched = await repo.get_by_id(obj.id)
    assert fetched is not None
    assert fetched.name == "create-1"


async def test_get_by_id_returns_none_for_missing(
    db_session: AsyncSession,
) -> None:
    repo = ConnectionRepository(db_session)
    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_update_applies_changes_dict(db_session: AsyncSession) -> None:
    repo = ConnectionRepository(db_session)
    obj = await repo.create(_make_connection("update-1"))
    updated = await repo.update(obj, {"description": "new", "is_active": False})
    assert updated.description == "new"
    assert updated.is_active is False
    fetched = await repo.get_by_id(obj.id)
    assert fetched is not None
    assert fetched.description == "new"


async def test_delete_removes_row(db_session: AsyncSession) -> None:
    repo = ConnectionRepository(db_session)
    obj = await repo.create(_make_connection("delete-1"))
    obj_id = obj.id
    await repo.delete(obj)
    assert await repo.get_by_id(obj_id) is None


def test_subclass_must_set_model() -> None:
    """A subclass that forgets to set ``model`` should fail noisily —
    not at runtime on the first ``get_by_id``. Kept lightweight: just
    verify the attribute exists and is the expected ORM class for the
    real subclass."""
    assert ConnectionRepository.model is OracleConnection


def test_subclass_without_model_raises_at_class_definition() -> None:
    """``__init_subclass__`` runs when a class body is evaluated, so
    forgetting ``model =`` should raise ``TypeError`` *immediately* —
    not on the first method call. Catch it via ``pytest.raises`` around
    a ``type()`` call so the bad class never enters the module
    namespace."""
    with pytest.raises(TypeError, match="must set a class attribute 'model'"):
        type("BrokenRepo", (BaseCrudRepository,), {})


def test_subclass_with_non_orm_model_raises() -> None:
    """``model`` must point at a real ORM class, not just any object."""
    with pytest.raises(TypeError, match="must be an ORM class deriving"):
        type("BrokenRepo2", (BaseCrudRepository,), {"model": "not-a-class"})


def test_base_init_signature() -> None:
    """All subclasses share the ``__init__(db)`` shape; pin it so a
    future refactor doesn't accidentally diverge."""
    import inspect

    sig = inspect.signature(BaseCrudRepository.__init__)
    assert list(sig.parameters) == ["self", "db"]
