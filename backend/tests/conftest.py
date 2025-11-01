from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import (
    WBE,
    AuditLog,
    BaselineLog,
    BaselineSnapshot,
    BudgetAllocation,
    ChangeOrder,
    CostElement,
    CostElementSchedule,
    CostElementType,
    CostRegistration,
    Department,
    EarnedValueEntry,
    Forecast,
    Item,
    Project,
    ProjectEvent,
    ProjectPhase,
    QualityEvent,
    User,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        init_db(session)
        yield session
        # Clean up all tables in reverse dependency order
        statement = delete(Item)
        session.execute(statement)
        statement = delete(
            EarnedValueEntry
        )  # Must be before CostElement/BaselineLog/User due to FK
        session.execute(statement)
        statement = delete(Forecast)  # Must be before CostElement/User due to FK
        session.execute(statement)
        statement = delete(
            CostElementSchedule
        )  # Must be before CostElement/BaselineLog/User due to FK
        session.execute(statement)
        statement = delete(
            CostRegistration
        )  # Must be before CostElement/User due to FK
        session.execute(statement)
        statement = delete(
            BudgetAllocation
        )  # Must be before CostElement/User due to FK
        session.execute(statement)
        statement = delete(CostElement)  # Must be before WBE due to FK
        session.execute(statement)
        statement = delete(WBE)  # Must be before Project due to FK
        session.execute(statement)
        statement = delete(
            QualityEvent
        )  # Must be before Project/WBE/CostElement due to FK
        session.execute(statement)
        statement = delete(ChangeOrder)  # Must be before Project due to FK
        session.execute(statement)
        statement = delete(ProjectEvent)  # Must be before Project due to FK
        session.execute(statement)
        statement = delete(BaselineSnapshot)  # Must be before Project due to FK
        session.execute(statement)
        statement = delete(Project)  # Must be before User due to FK
        session.execute(statement)
        statement = delete(BaselineLog)  # Must be before User due to FK
        session.execute(statement)
        statement = delete(AuditLog)  # Must be before User due to FK
        session.execute(statement)
        statement = delete(CostElementType)
        session.execute(statement)
        statement = delete(ProjectPhase)
        session.execute(statement)
        statement = delete(Department)
        session.execute(statement)
        statement = delete(User)
        session.execute(statement)
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
