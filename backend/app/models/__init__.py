"""
Models package for EVM Project Budget Management System.

This module serves as the main entry point for all database models.
It imports all models to ensure SQLModel metadata is properly registered.
"""

from sqlmodel import Field, SQLModel

from app.models.audit_log import (
    AuditLog,
    AuditLogBase,
    AuditLogCreate,
    AuditLogPublic,
    AuditLogUpdate,
)
from app.models.baseline_cost_element import (
    BaselineCostElement,
    BaselineCostElementBase,
    BaselineCostElementCreate,
    BaselineCostElementPublic,
    BaselineCostElementsByWBEPublic,
    BaselineCostElementsPublic,
    BaselineCostElementUpdate,
    BaselineCostElementWithCostElementPublic,
    WBEWithBaselineCostElementsPublic,
)
from app.models.baseline_log import (
    BaselineLog,
    BaselineLogBase,
    BaselineLogCreate,
    BaselineLogPublic,
    BaselineLogUpdate,
    BaselineSnapshotSummaryPublic,
    BaselineSummaryPublic,
)
from app.models.budget_allocation import (
    BudgetAllocation,
    BudgetAllocationBase,
    BudgetAllocationCreate,
    BudgetAllocationPublic,
    BudgetAllocationUpdate,
)
from app.models.budget_timeline import (
    CostElementWithSchedulePublic,
)
from app.models.change_order import (
    ChangeOrder,
    ChangeOrderBase,
    ChangeOrderCreate,
    ChangeOrderPublic,
    ChangeOrderUpdate,
)
from app.models.cost_category import (
    CostCategoriesPublic,
    CostCategoryPublic,
)
from app.models.cost_element import (
    CostElement,
    CostElementBase,
    CostElementCreate,
    CostElementPublic,
    CostElementsPublic,
    CostElementUpdate,
)
from app.models.cost_element_schedule import (
    CostElementSchedule,
    CostElementScheduleBase,
    CostElementScheduleCreate,
    CostElementSchedulePublic,
    CostElementScheduleUpdate,
)
from app.models.cost_element_type import (
    CostElementType,
    CostElementTypeBase,
    CostElementTypeCreate,
    CostElementTypePublic,
    CostElementTypesPublic,
    CostElementTypeUpdate,
)
from app.models.cost_registration import (
    CostRegistration,
    CostRegistrationBase,
    CostRegistrationCreate,
    CostRegistrationPublic,
    CostRegistrationsPublic,
    CostRegistrationUpdate,
)
from app.models.cost_summary import (
    CostSummaryBase,
    CostSummaryPublic,
)
from app.models.cost_timeline import (
    CostTimelinePointPublic,
    CostTimelinePublic,
)
from app.models.department import (
    Department,
    DepartmentBase,
    DepartmentCreate,
    DepartmentPublic,
    DepartmentUpdate,
)
from app.models.earned_value_entry import (
    EarnedValueEntriesPublic,
    EarnedValueEntry,
    EarnedValueEntryBase,
    EarnedValueEntryCreate,
    EarnedValueEntryPublic,
    EarnedValueEntryUpdate,
)
from app.models.forecast import (
    Forecast,
    ForecastBase,
    ForecastCreate,
    ForecastPublic,
    ForecastUpdate,
)
from app.models.project import (
    Project,
    ProjectBase,
    ProjectCreate,
    ProjectPublic,
    ProjectsPublic,
    ProjectUpdate,
)
from app.models.project_event import (
    ProjectEvent,
    ProjectEventBase,
    ProjectEventCreate,
    ProjectEventPublic,
    ProjectEventUpdate,
)
from app.models.project_phase import (
    ProjectPhase,
    ProjectPhaseBase,
    ProjectPhaseCreate,
    ProjectPhasePublic,
    ProjectPhaseUpdate,
)
from app.models.quality_event import (
    QualityEvent,
    QualityEventBase,
    QualityEventCreate,
    QualityEventPublic,
    QualityEventUpdate,
)

# Import shared models first
from app.models.user import (
    UpdatePassword,
    User,
    UserBase,
    UserCreate,
    UserPublic,
    UserRegister,
    UserRole,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.models.wbe import (
    WBE,
    WBEBase,
    WBECreate,
    WBEPublic,
    WBEsPublic,
    WBEUpdate,
)


# Generic models
class Message(SQLModel):
    """Generic message response."""

    message: str


class Token(SQLModel):
    """JSON payload containing access token."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(SQLModel):
    """Contents of JWT token."""

    sub: str | None = None


class NewPassword(SQLModel):
    """Password reset request."""

    token: str
    new_password: str = Field(min_length=8, max_length=128)


__all__ = [
    # User models
    "User",
    "UserBase",
    "UserCreate",
    "UserPublic",
    "UserRegister",
    "UserRole",
    "UserUpdate",
    "UserUpdateMe",
    "UsersPublic",
    "UpdatePassword",
    # Department models
    "Department",
    "DepartmentBase",
    "DepartmentCreate",
    "DepartmentPublic",
    "DepartmentUpdate",
    # Cost Element Type models
    "CostElementType",
    "CostElementTypeBase",
    "CostElementTypeCreate",
    "CostElementTypePublic",
    "CostElementTypesPublic",
    "CostElementTypeUpdate",
    # Cost Category models
    "CostCategoryPublic",
    "CostCategoriesPublic",
    # Project Phase models
    "ProjectPhase",
    "ProjectPhaseBase",
    "ProjectPhaseCreate",
    "ProjectPhasePublic",
    "ProjectPhaseUpdate",
    # Project models
    "Project",
    "ProjectBase",
    "ProjectCreate",
    "ProjectsPublic",
    "ProjectPublic",
    "ProjectUpdate",
    # Project Event models
    "ProjectEvent",
    "ProjectEventBase",
    "ProjectEventCreate",
    "ProjectEventPublic",
    "ProjectEventUpdate",
    # WBE models
    "WBE",
    "WBEBase",
    "WBECreate",
    "WBEPublic",
    "WBEsPublic",
    "WBEUpdate",
    # Cost Element models
    "CostElement",
    "CostElementBase",
    "CostElementCreate",
    "CostElementPublic",
    "CostElementsPublic",
    "CostElementUpdate",
    # Audit Log models
    "AuditLog",
    "AuditLogBase",
    "AuditLogCreate",
    "AuditLogPublic",
    "AuditLogUpdate",
    # Baseline Log models
    "BaselineLog",
    "BaselineLogBase",
    "BaselineLogCreate",
    "BaselineLogPublic",
    "BaselineLogUpdate",
    # Baseline Cost Element models
    "BaselineCostElement",
    "BaselineCostElementBase",
    "BaselineCostElementCreate",
    "BaselineCostElementPublic",
    "BaselineCostElementUpdate",
    "BaselineCostElementWithCostElementPublic",
    "BaselineCostElementsByWBEPublic",
    "BaselineCostElementsPublic",
    "WBEWithBaselineCostElementsPublic",
    # Baseline summary models
    "BaselineSummaryPublic",
    "BaselineSnapshotSummaryPublic",
    # Change Order models
    "ChangeOrder",
    "ChangeOrderBase",
    "ChangeOrderCreate",
    "ChangeOrderPublic",
    "ChangeOrderUpdate",
    # Quality Event models
    "QualityEvent",
    "QualityEventBase",
    "QualityEventCreate",
    "QualityEventPublic",
    "QualityEventUpdate",
    # Budget Allocation models
    "BudgetAllocation",
    "BudgetAllocationBase",
    "BudgetAllocationCreate",
    "BudgetAllocationPublic",
    "BudgetAllocationUpdate",
    # Budget Timeline models
    "CostElementWithSchedulePublic",
    # Cost Registration models
    "CostRegistration",
    "CostRegistrationBase",
    "CostRegistrationCreate",
    "CostRegistrationPublic",
    "CostRegistrationsPublic",
    "CostRegistrationUpdate",
    # Cost Summary models
    "CostSummaryBase",
    "CostSummaryPublic",
    # Cost Timeline models
    "CostTimelinePointPublic",
    "CostTimelinePublic",
    # Cost Element Schedule models
    "CostElementSchedule",
    "CostElementScheduleBase",
    "CostElementScheduleCreate",
    "CostElementSchedulePublic",
    "CostElementScheduleUpdate",
    # Earned Value Entry models
    "EarnedValueEntriesPublic",
    "EarnedValueEntry",
    "EarnedValueEntryBase",
    "EarnedValueEntryCreate",
    "EarnedValueEntryPublic",
    "EarnedValueEntryUpdate",
    # Forecast models
    "Forecast",
    "ForecastBase",
    "ForecastCreate",
    "ForecastPublic",
    "ForecastUpdate",
    # Shared models
    "Message",
    "Token",
    "TokenPayload",
    "NewPassword",
    # SQLModel base
    "SQLModel",
]
