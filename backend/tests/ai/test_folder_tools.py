"""Tests for the ``list_folders`` / ``create_folder`` / ``delete_folder`` AI tools.

The tools instantiate ``DocumentFolderService(context.session)`` internally, so
we patch ``app.ai.tools.document_tools.DocumentFolderService`` with a
``MagicMock`` whose ``get_folder_tree`` / ``create_folder`` / ``delete_folder``
are ``AsyncMock`` returning stub folder objects. This keeps every test DB-free.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.tools.document_tools import create_folder, delete_folder, list_folders
from app.ai.tools.types import ToolContext

# ``@ai_tool`` replaces the module names with LangChain ``StructuredTool``s.
# ``.coroutine`` is the decorator's session-managing wrapper and
# ``__wrapped__`` is the original async function with no session side effects
# -- what we want for a pure unit test.
_list_folders_raw = list_folders.coroutine.__wrapped__  # type: ignore[attr-defined]
_create_folder_raw = create_folder.coroutine.__wrapped__  # type: ignore[attr-defined]
_delete_folder_raw = delete_folder.coroutine.__wrapped__  # type: ignore[attr-defined]

_USER_ID = "00000000-0000-0000-0000-000000000001"
_PROJECT_ID = "00000000-0000-0000-0000-0000000000aa"
_FOLDER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000f1")
_PARENT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000fa")


class _StubFolder:
    """Minimal stand-in for a DocumentFolder ORM row.

    Only attributes read by the folder tools' result dicts are set.
    """

    def __init__(
        self,
        *,
        folder_id: uuid.UUID = _FOLDER_ID,
        name: str = "Reports",
        path: str = "/Reports",
        parent_id: uuid.UUID | None = None,
    ) -> None:
        self.id = folder_id
        self.name = name
        self.path = path
        self.parent_id = parent_id


def _make_context(project_id: str | None = _PROJECT_ID) -> ToolContext:
    return ToolContext(
        session=MagicMock(),
        user_id=_USER_ID,
        project_id=project_id,
    )


def _patch_folder_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    get_folder_tree_return: Any = None,
    get_folder_tree_side_effect: Any = None,
    create_folder_return: Any = None,
    create_folder_side_effect: Any = None,
    delete_folder_return: Any = None,
    delete_folder_side_effect: Any = None,
) -> MagicMock:
    """Patch ``DocumentFolderService`` in the tool module with a controlled mock.

    Returns the mock service instance so tests can assert on call args.
    """
    service_instance = MagicMock()

    if get_folder_tree_side_effect is not None:
        service_instance.get_folder_tree = AsyncMock(
            side_effect=get_folder_tree_side_effect
        )
    else:
        service_instance.get_folder_tree = AsyncMock(
            return_value=get_folder_tree_return or []
        )

    if create_folder_side_effect is not None:
        service_instance.create_folder = AsyncMock(
            side_effect=create_folder_side_effect
        )
    else:
        service_instance.create_folder = AsyncMock(
            return_value=create_folder_return or _StubFolder()
        )

    if delete_folder_side_effect is not None:
        service_instance.delete_folder = AsyncMock(
            side_effect=delete_folder_side_effect
        )
    else:
        service_instance.delete_folder = AsyncMock(
            return_value=delete_folder_return
            if delete_folder_return is not None
            else True
        )

    mock_service_cls = MagicMock(return_value=service_instance)
    monkeypatch.setattr(
        "app.ai.tools.document_tools.DocumentFolderService", mock_service_cls
    )
    return service_instance


# ---------------------------------------------------------------------------
# list_folders
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_folders_returns_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_folders returns the folder list and total count."""
    folders = [
        _StubFolder(folder_id=_PARENT_ID, name="Reports", path="/Reports"),
        _StubFolder(
            folder_id=_FOLDER_ID,
            name="Invoices",
            path="/Reports/Invoices",
            parent_id=_PARENT_ID,
        ),
    ]
    _patch_folder_service(monkeypatch, get_folder_tree_return=folders)
    ctx = _make_context()

    result = await _list_folders_raw(context=ctx)

    assert "error" not in result
    assert result["total"] == 2
    assert result["folders"][0]["id"] == str(_PARENT_ID)
    assert result["folders"][0]["parent_id"] is None
    assert result["folders"][1]["parent_id"] == str(_PARENT_ID)
    assert result["folders"][1]["path"] == "/Reports/Invoices"


@pytest.mark.asyncio
async def test_list_folders_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_folders with no folders returns an empty list and total 0."""
    _patch_folder_service(monkeypatch, get_folder_tree_return=[])
    ctx = _make_context()

    result = await _list_folders_raw(context=ctx)

    assert "error" not in result
    assert result["total"] == 0
    assert result["folders"] == []


@pytest.mark.asyncio
async def test_list_folders_no_project_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """When project_id is None, list_folders returns the 'No project context' error."""
    _patch_folder_service(monkeypatch)
    ctx = _make_context(project_id=None)

    result = await _list_folders_raw(context=ctx)

    assert "error" in result
    assert "No project context" in result["error"]


# ---------------------------------------------------------------------------
# create_folder
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_folder_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Root folder (parent_id=None) is created with parent_id None in the result."""
    stub = _StubFolder(name="Reports", path="/Reports", parent_id=None)
    service = _patch_folder_service(monkeypatch, create_folder_return=stub)
    ctx = _make_context()

    result = await _create_folder_raw(name="Reports", context=ctx)

    assert "error" not in result
    assert result["id"] == str(_FOLDER_ID)
    assert result["name"] == "Reports"
    assert result["path"] == "/Reports"
    assert result["parent_id"] is None
    assert result["message"] == "Folder 'Reports' created successfully"
    # DocumentFolderCreate must have parent_id=None
    sent_data = service.create_folder.call_args.args[1]
    assert sent_data.parent_id is None
    assert sent_data.name == "Reports"


@pytest.mark.asyncio
async def test_create_folder_nested(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nested folder (parent_id given) is created with parent_id set in the result."""
    stub = _StubFolder(
        name="Invoices",
        path="/Reports/Invoices",
        parent_id=_PARENT_ID,
    )
    service = _patch_folder_service(monkeypatch, create_folder_return=stub)
    ctx = _make_context()

    result = await _create_folder_raw(
        name="Invoices", parent_id=str(_PARENT_ID), context=ctx
    )

    assert "error" not in result
    assert result["parent_id"] == str(_PARENT_ID)
    assert result["path"] == "/Reports/Invoices"
    # DocumentFolderCreate must carry the parsed UUID
    sent_data = service.create_folder.call_args.args[1]
    assert sent_data.parent_id == _PARENT_ID


@pytest.mark.asyncio
async def test_create_folder_bad_parent_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ValueError from create_folder (bad parent) -> error dict."""
    _patch_folder_service(
        monkeypatch,
        create_folder_side_effect=ValueError("Parent folder <bad> not found"),
    )
    ctx = _make_context()

    result = await _create_folder_raw(
        name="Invoices", parent_id=str(_PARENT_ID), context=ctx
    )

    assert "error" in result
    assert "Invalid input" in result["error"]
    assert "Parent folder" in result["error"]


@pytest.mark.asyncio
async def test_create_folder_no_project_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When project_id is None, create_folder returns the 'No project context' error."""
    _patch_folder_service(monkeypatch)
    ctx = _make_context(project_id=None)

    result = await _create_folder_raw(name="Reports", context=ctx)

    assert "error" in result
    assert "No project context" in result["error"]


# ---------------------------------------------------------------------------
# delete_folder
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_folder_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful delete returns folder_id and confirmation message."""
    _patch_folder_service(monkeypatch, delete_folder_return=True)
    ctx = _make_context()

    result = await _delete_folder_raw(folder_id=str(_FOLDER_ID), context=ctx)

    assert "error" not in result
    assert result["folder_id"] == str(_FOLDER_ID)
    assert "deleted" in result["message"]


@pytest.mark.asyncio
async def test_delete_folder_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Service returning False -> 'not found' error."""
    _patch_folder_service(monkeypatch, delete_folder_return=False)
    ctx = _make_context()

    result = await _delete_folder_raw(folder_id=str(_FOLDER_ID), context=ctx)

    assert "error" in result
    assert "not found" in result["error"]
    assert str(_FOLDER_ID) in result["error"]


@pytest.mark.asyncio
async def test_delete_folder_no_project_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When project_id is None, delete_folder returns the 'No project context' error."""
    _patch_folder_service(monkeypatch)
    ctx = _make_context(project_id=None)

    result = await _delete_folder_raw(folder_id=str(_FOLDER_ID), context=ctx)

    assert "error" in result
    assert "No project context" in result["error"]
