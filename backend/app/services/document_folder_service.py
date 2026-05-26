"""Document folder service - CRUD and tree management for folder hierarchy."""

import logging
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.document_folder import DocumentFolder
from app.models.schemas.document import DocumentFolderCreate

logger = logging.getLogger(__name__)


class DocumentFolderService:
    """Service for managing document folder trees within a project."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_folder(
        self,
        project_id: UUID,
        data: DocumentFolderCreate,
        user_id: UUID,
    ) -> DocumentFolder:
        """Create a new folder with a computed path.

        Root folders have path ``/{name}``. Child folders inherit the
        parent path and append ``/{name}``.

        Args:
            project_id: Project the folder belongs to.
            data: Folder creation payload.
            user_id: ID of the user creating the folder.

        Returns:
            The created folder.

        Raises:
            ValueError: If ``parent_id`` is provided but does not exist
                in the same project.
        """
        if data.parent_id is not None:
            parent = await self._get_folder(data.parent_id)
            if parent is None or parent.project_id != str(project_id):
                raise ValueError(f"Parent folder {data.parent_id} not found")
            path = f"{parent.path}/{data.name}"
        else:
            path = f"/{data.name}"

        folder = DocumentFolder(
            project_id=project_id,
            parent_id=data.parent_id,
            name=data.name,
            path=path,
            created_by=user_id,
        )
        self.db.add(folder)
        await self.db.flush()
        await self.db.refresh(folder)
        logger.info(
            "Folder created: %s (path=%s) in project %s",
            folder.name,
            folder.path,
            project_id,
        )
        return folder

    async def get_folder(self, folder_id: UUID) -> DocumentFolder | None:
        """Fetch a single folder by ID.

        Args:
            folder_id: Primary key of the folder.

        Returns:
            The folder if found, None otherwise.
        """
        return await self._get_folder(folder_id)

    async def get_folder_tree(self, project_id: UUID) -> list[DocumentFolder]:
        """Return all folders for a project, ordered by path.

        Args:
            project_id: Project to fetch folders for.

        Returns:
            Ordered list of folders.
        """
        stmt = (
            select(DocumentFolder)
            .where(DocumentFolder.project_id == project_id)
            .order_by(DocumentFolder.path)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def rename_folder(self, folder_id: UUID, name: str) -> DocumentFolder:
        """Rename a folder and recompute paths for it and all descendants.

        Args:
            folder_id: Primary key of the folder to rename.
            name: New name for the folder.

        Returns:
            The updated folder.

        Raises:
            ValueError: If the folder does not exist.
        """
        folder = await self._get_folder(folder_id)
        if folder is None:
            raise ValueError(f"Folder {folder_id} not found")

        old_path = folder.path
        # Compute new path: replace the last segment
        parent_prefix = old_path.rsplit("/", 1)[0]
        new_path = f"{parent_prefix}/{name}"

        await self._recompute_paths(old_path, new_path)

        folder.name = name
        folder.path = new_path
        await self.db.flush()
        await self.db.refresh(folder)
        logger.info("Folder renamed: %s -> %s", old_path, new_path)
        return folder

    async def move_folder(
        self, folder_id: UUID, new_parent_id: UUID | None
    ) -> DocumentFolder:
        """Move a folder under a new parent and recompute paths.

        Args:
            folder_id: Primary key of the folder to move.
            new_parent_id: New parent folder ID, or None for root.

        Returns:
            The updated folder.

        Raises:
            ValueError: If the folder or new parent does not exist.
        """
        folder = await self._get_folder(folder_id)
        if folder is None:
            raise ValueError(f"Folder {folder_id} not found")

        old_path = folder.path

        if new_parent_id is not None:
            new_parent = await self._get_folder(new_parent_id)
            if new_parent is None:
                raise ValueError(f"Parent folder {new_parent_id} not found")
            new_path = f"{new_parent.path}/{folder.name}"
        else:
            new_path = f"/{folder.name}"

        folder.parent_id = str(new_parent_id) if new_parent_id else None
        await self._recompute_paths(old_path, new_path)

        folder.path = new_path
        await self.db.flush()
        await self.db.refresh(folder)
        logger.info("Folder moved: %s -> %s", old_path, new_path)
        return folder

    async def delete_folder(
        self, folder_id: UUID, project_id: UUID | None = None
    ) -> bool:
        """Delete a folder and all its descendants.

        Note: documents contained in deleted folders should be moved or
        deleted by the caller before invoking this method.

        Args:
            folder_id: Primary key of the folder to delete.
            project_id: If provided, scopes the lookup to this project.

        Returns:
            True if the folder was deleted, False if not found.
        """
        folder = await self._get_folder(folder_id)
        if folder is None:
            return False

        if project_id is not None and folder.project_id != str(project_id):
            return False

        # Delete all descendants (paths that start with folder path + /)
        # plus the folder itself (path matches exactly or starts with path/)
        path_prefix = folder.path + "/"
        stmt = delete(DocumentFolder).where(
            (DocumentFolder.path == folder.path)
            | (DocumentFolder.path.startswith(path_prefix))
        )
        await self.db.execute(stmt)
        await self.db.flush()
        logger.info("Folder deleted: %s (path=%s)", folder_id, folder.path)
        return True

    # --- Internal helpers ---

    async def _get_folder(self, folder_id: UUID) -> DocumentFolder | None:
        """Fetch a folder by primary key."""
        stmt = select(DocumentFolder).where(DocumentFolder.id == folder_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _recompute_paths(self, old_prefix: str, new_prefix: str) -> None:
        """Update paths for all folders whose path starts with old_prefix.

        Replaces the old_prefix portion of each matching path with
        new_prefix. This handles both the folder itself and all
        descendant folders.

        Args:
            old_prefix: The current path prefix to replace.
            new_prefix: The replacement path prefix.
        """
        prefix_len = len(old_prefix)
        stmt = (
            update(DocumentFolder)
            .where(
                (DocumentFolder.path == old_prefix)
                | (DocumentFolder.path.startswith(old_prefix + "/"))
            )
            .values(
                path=func.concat(
                    new_prefix, func.substr(DocumentFolder.path, prefix_len + 1)
                )
            )
        )
        await self.db.execute(stmt)
