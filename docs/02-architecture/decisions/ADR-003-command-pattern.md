# ADR-003: Command Pattern for Write Operations

## Status

✅ Accepted (2025-12-28)

## Context

The Backcast EVS system uses versioning for entities, where each write operation (create, update, delete) must:

- Create new version records
- Close previous versions
- Maintain audit trails
- Support undo capabilities

We needed a consistent pattern for implementing these operations across all entities that:

- Encapsulates the complexity of version management
- Provides clear interfaces for each operation type
- Supports transaction management
- Enables undo/rollback capabilities

## Decision

Adopt the **Command Pattern** for all write operations on versioned entities.

### Core Design

Each write operation is encapsulated in a Command class:

```python
class VersionCommand[T](ABC):
    """Abstract base for versioning commands."""

    def __init__(self, metadata: CommandMetadata):
        self.metadata = metadata

    @abstractmethod
    async def execute(self, session: AsyncSession) -> T:
        """Execute the command."""
        pass

    @abstractmethod
    async def undo(self, session: AsyncSession) -> None:
        """Undo the command (if possible)."""
        pass
```

### Command Types

| Command               | Purpose                                         |
| --------------------- | ----------------------------------------------- |
| `CreateCommand`       | Create new entity with initial version          |
| `UpdateCommand`       | Close current version, create new with changes  |
| `DeleteCommand`       | Soft delete (set is_active=False or deleted_at) |
| `CreateBranchCommand` | Clone version to new branch                     |
| `MergeBranchCommand`  | Merge source branch to target                   |
| `RevertCommand`       | Restore previous version state                  |

### Command Metadata

Each command carries metadata for audit trail:

```python
@dataclass
class CommandMetadata:
    command_type: str      # "CREATE_USER", "UPDATE_PROJECT", etc.
    user_id: UUID          # Who executed the command
    timestamp: datetime    # When executed
    description: str       # Human-readable description
    branch: str = "main"   # Target branch
```

## Consequences

### Positive

- **Encapsulation:** Version management logic contained in reusable classes
- **Audit Trail:** Metadata automatically captured for each operation
- **Undo Support:** Commands can implement reversible operations
- **Testability:** Commands can be unit tested in isolation
- **Consistency:** All entities use same patterns for CRUD
- **Transaction Safety:** Commands don't commit, caller controls transaction

### Negative

- **Verbosity:** More classes than simple repository methods
- **Learning Curve:** Team must understand command pattern
- **Indirection:** Additional layer between service and database

## Implementation Notes

Commands are executed via services:

```python
class UserService:
    async def update_user(self, user_id: UUID, data: UserUpdate, actor_id: UUID) -> User:
        metadata = CommandMetadata(
            command_type="UPDATE_USER",
            user_id=actor_id,
            timestamp=datetime.now(UTC),
            description="User profile update",
        )
        command = UpdateUserCommand(metadata=metadata, user_id=user_id, changes=data.dict())
        return await command.execute(self.session)
```

## Related Documentation

- [EVCS Core Architecture](../backend/contexts/evcs-core/architecture.md) - Generic commands
- [ADR-005: Bitemporal Versioning](ADR-005-bitemporal-versioning.md) - Updated command design
