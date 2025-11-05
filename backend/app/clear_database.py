import logging

from sqlmodel import Session, delete

from app.core.db import engine
from app.models import (
    WBE,
    AuditLog,
    BaselineCostElement,
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
    Project,
    ProjectEvent,
    ProjectPhase,
    QualityEvent,
    User,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_db() -> None:
    """Clear all data from the database in reverse dependency order."""
    with Session(engine) as session:
        logger.info("Clearing database tables...")

        # Delete records in reverse dependency order to respect foreign key constraints
        # Start with tables that reference other tables
        logger.info("Deleting EarnedValueEntry...")
        session.execute(delete(EarnedValueEntry))

        logger.info("Deleting Forecast...")
        session.execute(delete(Forecast))

        logger.info("Deleting CostElementSchedule...")
        session.execute(delete(CostElementSchedule))

        logger.info("Deleting CostRegistration...")
        session.execute(delete(CostRegistration))

        logger.info("Deleting BudgetAllocation...")
        session.execute(delete(BudgetAllocation))

        logger.info("Deleting BaselineCostElement...")
        session.execute(delete(BaselineCostElement))

        logger.info("Deleting CostElement...")
        session.execute(delete(CostElement))

        logger.info("Deleting WBE...")
        session.execute(delete(WBE))

        logger.info("Deleting QualityEvent...")
        session.execute(delete(QualityEvent))

        logger.info("Deleting ChangeOrder...")
        session.execute(delete(ChangeOrder))

        logger.info("Deleting ProjectEvent...")
        session.execute(delete(ProjectEvent))

        logger.info("Deleting BaselineSnapshot...")
        session.execute(delete(BaselineSnapshot))

        logger.info("Deleting BaselineLog...")
        session.execute(delete(BaselineLog))

        logger.info("Deleting Project...")
        session.execute(delete(Project))

        logger.info("Deleting AuditLog...")
        session.execute(delete(AuditLog))

        logger.info("Deleting CostElementType...")
        session.execute(delete(CostElementType))

        logger.info("Deleting ProjectPhase...")
        session.execute(delete(ProjectPhase))

        logger.info("Deleting Department...")
        session.execute(delete(Department))

        logger.info("Deleting User...")
        session.execute(delete(User))

        session.commit()
        logger.info("Database cleared successfully")


def main() -> None:
    logger.info("Starting database clearing process")
    clear_db()
    logger.info("Database clearing completed")


if __name__ == "__main__":
    main()
