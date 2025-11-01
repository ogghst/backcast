"""
Test that all models can be imported from the new models/ directory structure.
This ensures backward compatibility and proper module organization.
"""


def test_user_models_can_be_imported():
    """Test that User models can be imported from new location."""
    from app.models.user import (
        User,
        UserBase,
        UserCreate,
        UserPublic,
        UserUpdate,
    )

    # Verify classes exist and are importable
    assert User is not None
    assert UserBase is not None
    assert UserCreate is not None
    assert UserPublic is not None
    assert UserUpdate is not None


def test_item_models_can_be_imported():
    """Test that Item models can be imported from new location."""
    from app.models.item import (
        Item,
        ItemBase,
        ItemCreate,
        ItemPublic,
        ItemUpdate,
    )

    # Verify classes exist and are importable
    assert Item is not None
    assert ItemBase is not None
    assert ItemCreate is not None
    assert ItemPublic is not None
    assert ItemUpdate is not None


def test_all_models_importable_from_main_module():
    """Test that models can be imported from app.models for backward compatibility."""
    from app.models import (
        # Item models
        Item,
        Message,
        SQLModel,
        Token,
        User,
    )

    # Verify all classes exist
    assert User is not None
    assert Item is not None
    assert Message is not None
    assert Token is not None
    assert SQLModel is not None


def test_user_model_structure_unchanged(db):
    """
    Test that User model structure is identical to original after migration.
    This ensures we haven't broken existing functionality.
    """
    import uuid

    from app import crud
    from app.models import UserCreate

    # Create a user using existing CRUD operations with unique email
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    # Verify user was created correctly
    assert user.id is not None
    assert user.email == email
    assert hasattr(user, "hashed_password")
    assert user.is_active is True
    assert hasattr(user, "items")  # Relationship should exist


def test_item_model_structure_unchanged(db):
    """
    Test that Item model structure is identical to original after migration.
    This ensures we haven't broken existing functionality.
    """
    import uuid

    from app import crud
    from app.models import ItemCreate, UserCreate

    # Create a user first with unique email
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    # Create an item for that user
    item_in = ItemCreate(title="Test Item", description="Test Description")
    item = crud.create_item(session=db, item_in=item_in, owner_id=user.id)

    # Verify item was created correctly
    assert item.id is not None
    assert item.title == "Test Item"
    assert item.description == "Test Description"
    assert item.owner_id == user.id
    assert hasattr(item, "owner")  # Relationship should exist
