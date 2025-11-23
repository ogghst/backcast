from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.core.seeds import (
    _seed_ai_default_config,
    _seed_cost_element_types,
    _seed_departments,
    _seed_project_from_template,
    _seed_variance_threshold_configs,
)
from app.models import User, UserCreate, UserRole

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    # Ensure session is in a good state before proceeding
    try:
        session.rollback()
    except Exception:
        pass  # Ignore if already rolled back or no transaction

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            role=UserRole.admin,
        )
        user = crud.create_user(session=session, user_create=user_in)

    # Seed departments first (cost element types depend on departments)
    _seed_departments(session)
    # Seed cost element types
    _seed_cost_element_types(session)
    # Seed variance threshold configurations (no dependencies)
    _seed_variance_threshold_configs(session)
    # Seed AI default configuration (no dependencies)
    _seed_ai_default_config(session)
    # Seed project from template (depends on departments, cost element types, and user)
    _seed_project_from_template(session)
