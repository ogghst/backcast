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


def test_all_models_importable_from_main_module():
    """Test that models can be imported from app.models for backward compatibility."""
    from app.models import (
        Message,
        SQLModel,
        Token,
        User,
    )

    # Verify all classes exist
    assert User is not None
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
