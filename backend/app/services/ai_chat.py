"""AI chat service for generating project assessments."""

import uuid
from collections.abc import Awaitable, Callable
from datetime import date
from decimal import Decimal
from typing import Any, Literal, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from sqlmodel import Session, select

# Import helper functions from API routes (reused logic)
from app.api.routes.evm_aggregation import _get_entry_map, _get_schedule_map
from app.core.encryption import decrypt_api_key
from app.models import (
    WBE,
    AppConfiguration,
    BaselineCostElement,
    BaselineLog,
    CostElement,
    CostRegistration,
    Project,
    User,
)
from app.services.evm_aggregation import (
    aggregate_cost_element_metrics,
    get_cost_element_evm_metrics,
)
from app.services.evm_indices import (
    calculate_cost_variance,
    calculate_cpi,
    calculate_schedule_variance,
    calculate_spi,
    calculate_tcpi,
)
from app.services.time_machine import (
    TimeMachineEventType,
    apply_time_machine_filters,
    end_of_day,
)

ContextType = Literal["project", "wbe", "cost-element", "baseline"]


def collect_context_metrics(
    session: Session,
    context_type: ContextType,
    context_id: uuid.UUID,
    control_date: date,
) -> dict:
    """
    Collect metrics based on context type.

    Args:
        session: Database session
        context_type: Type of context (project, wbe, cost-element, baseline)
        context_id: ID of the context entity
        control_date: Control date for time-machine filtering

    Returns:
        Dictionary with context-specific metrics for AI assessment

    Raises:
        ValueError: If context_type is invalid or context entity not found
    """
    if context_type == "project":
        return _collect_project_metrics(session, context_id, control_date)
    elif context_type == "wbe":
        return _collect_wbe_metrics(session, context_id, control_date)
    elif context_type == "cost-element":
        return _collect_cost_element_metrics(session, context_id, control_date)
    elif context_type == "baseline":
        return _collect_baseline_metrics(session, context_id, control_date)
    else:
        raise ValueError(
            f"Invalid context_type: {context_type}. "
            "Must be one of: project, wbe, cost-element, baseline"
        )


def _collect_project_metrics(
    session: Session, project_id: uuid.UUID, control_date: date
) -> dict:
    """Collect metrics for a project by aggregating from all WBEs."""
    project = session.get(Project, project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    # Get all WBEs for project (respecting control date)
    cutoff = end_of_day(control_date)
    wbes = session.exec(
        select(WBE).where(
            WBE.project_id == project_id,
            WBE.created_at <= cutoff,
        )
    ).all()

    # Get all cost elements for project (respecting control date)
    cost_elements = session.exec(
        select(CostElement)
        .join(WBE)
        .where(
            WBE.project_id == project_id,
            CostElement.created_at <= cutoff,
        )
    ).all()

    if not cost_elements:
        # Return empty metrics
        return {
            "context_type": "project",
            "project_id": str(project.project_id),
            "project_name": project.project_name,
            "control_date": control_date.isoformat(),
            "planned_value": Decimal("0.00"),
            "earned_value": Decimal("0.00"),
            "actual_cost": Decimal("0.00"),
            "budget_bac": Decimal("0.00"),
            "cpi": None,
            "spi": None,
            "tcpi": None,
            "cost_variance": Decimal("0.00"),
            "schedule_variance": Decimal("0.00"),
            "wbe_count": 0,
            "cost_element_count": 0,
        }

    cost_element_ids = [ce.cost_element_id for ce in cost_elements]

    # Get schedules, entries, and cost registrations
    schedule_map = _get_schedule_map(session, cost_element_ids, control_date)
    entry_map = _get_entry_map(session, cost_element_ids, control_date)

    statement = select(CostRegistration).where(
        CostRegistration.cost_element_id.in_(cost_element_ids),
    )
    statement = apply_time_machine_filters(
        statement, TimeMachineEventType.COST_REGISTRATION, control_date
    )
    all_cost_registrations = session.exec(statement).all()

    # Group cost registrations by cost element
    cost_registrations_by_ce: dict[uuid.UUID, list[CostRegistration]] = {}
    for cr in all_cost_registrations:
        if cr.cost_element_id not in cost_registrations_by_ce:
            cost_registrations_by_ce[cr.cost_element_id] = []
        cost_registrations_by_ce[cr.cost_element_id].append(cr)

    # Calculate metrics for each cost element
    cost_element_metrics = []
    for cost_element in cost_elements:
        metrics = get_cost_element_evm_metrics(
            cost_element=cost_element,
            schedule=schedule_map.get(cost_element.cost_element_id),
            entry=entry_map.get(cost_element.cost_element_id),
            cost_registrations=cost_registrations_by_ce.get(
                cost_element.cost_element_id, []
            ),
            control_date=control_date,
        )
        cost_element_metrics.append(metrics)

    # Aggregate metrics
    aggregated = aggregate_cost_element_metrics(cost_element_metrics)

    return {
        "context_type": "project",
        "project_id": str(project.project_id),
        "project_name": project.project_name,
        "control_date": control_date.isoformat(),
        "planned_value": float(aggregated.planned_value),
        "earned_value": float(aggregated.earned_value),
        "actual_cost": float(aggregated.actual_cost),
        "budget_bac": float(aggregated.budget_bac),
        "cpi": float(aggregated.cpi) if aggregated.cpi else None,
        "spi": float(aggregated.spi) if aggregated.spi else None,
        "tcpi": (
            float(aggregated.tcpi)
            if isinstance(aggregated.tcpi, Decimal)
            else aggregated.tcpi
        ),
        "cost_variance": float(aggregated.cost_variance),
        "schedule_variance": float(aggregated.schedule_variance),
        "wbe_count": len(wbes),
        "cost_element_count": len(cost_elements),
    }


def _collect_wbe_metrics(
    session: Session, wbe_id: uuid.UUID, control_date: date
) -> dict:
    """Collect metrics for a WBE by aggregating from all cost elements."""
    wbe = session.get(WBE, wbe_id)
    if not wbe:
        raise ValueError(f"WBE {wbe_id} not found")

    project = session.get(Project, wbe.project_id)
    if not project:
        raise ValueError(f"Project {wbe.project_id} not found")

    # Get all cost elements for WBE (respecting control date)
    cutoff = end_of_day(control_date)
    cost_elements = session.exec(
        select(CostElement).where(
            CostElement.wbe_id == wbe_id,
            CostElement.created_at <= cutoff,
        )
    ).all()

    if not cost_elements:
        # Return empty metrics
        return {
            "context_type": "wbe",
            "wbe_id": str(wbe.wbe_id),
            "wbe_name": wbe.machine_type,
            "project_id": str(wbe.project_id),
            "project_name": project.project_name,
            "control_date": control_date.isoformat(),
            "planned_value": Decimal("0.00"),
            "earned_value": Decimal("0.00"),
            "actual_cost": Decimal("0.00"),
            "budget_bac": Decimal("0.00"),
            "cpi": None,
            "spi": None,
            "tcpi": None,
            "cost_variance": Decimal("0.00"),
            "schedule_variance": Decimal("0.00"),
            "cost_element_count": 0,
        }

    cost_element_ids = [ce.cost_element_id for ce in cost_elements]

    # Get schedules, entries, and cost registrations
    schedule_map = _get_schedule_map(session, cost_element_ids, control_date)
    entry_map = _get_entry_map(session, cost_element_ids, control_date)

    statement = select(CostRegistration).where(
        CostRegistration.cost_element_id.in_(cost_element_ids),
    )
    statement = apply_time_machine_filters(
        statement, TimeMachineEventType.COST_REGISTRATION, control_date
    )
    all_cost_registrations = session.exec(statement).all()

    # Group cost registrations by cost element
    cost_registrations_by_ce: dict[uuid.UUID, list[CostRegistration]] = {}
    for cr in all_cost_registrations:
        if cr.cost_element_id not in cost_registrations_by_ce:
            cost_registrations_by_ce[cr.cost_element_id] = []
        cost_registrations_by_ce[cr.cost_element_id].append(cr)

    # Calculate metrics for each cost element
    cost_element_metrics = []
    for cost_element in cost_elements:
        metrics = get_cost_element_evm_metrics(
            cost_element=cost_element,
            schedule=schedule_map.get(cost_element.cost_element_id),
            entry=entry_map.get(cost_element.cost_element_id),
            cost_registrations=cost_registrations_by_ce.get(
                cost_element.cost_element_id, []
            ),
            control_date=control_date,
        )
        cost_element_metrics.append(metrics)

    # Aggregate metrics
    aggregated = aggregate_cost_element_metrics(cost_element_metrics)

    return {
        "context_type": "wbe",
        "wbe_id": str(wbe.wbe_id),
        "wbe_name": wbe.machine_type,
        "project_id": str(wbe.project_id),
        "project_name": project.project_name,
        "control_date": control_date.isoformat(),
        "planned_value": float(aggregated.planned_value),
        "earned_value": float(aggregated.earned_value),
        "actual_cost": float(aggregated.actual_cost),
        "budget_bac": float(aggregated.budget_bac),
        "cpi": float(aggregated.cpi) if aggregated.cpi else None,
        "spi": float(aggregated.spi) if aggregated.spi else None,
        "tcpi": (
            float(aggregated.tcpi)
            if isinstance(aggregated.tcpi, Decimal)
            else aggregated.tcpi
        ),
        "cost_variance": float(aggregated.cost_variance),
        "schedule_variance": float(aggregated.schedule_variance),
        "cost_element_count": len(cost_elements),
    }


def _collect_cost_element_metrics(
    session: Session, cost_element_id: uuid.UUID, control_date: date
) -> dict:
    """Collect metrics for a single cost element."""
    cost_element = session.get(CostElement, cost_element_id)
    if not cost_element:
        raise ValueError(f"Cost element {cost_element_id} not found")

    wbe = session.get(WBE, cost_element.wbe_id)
    if not wbe:
        raise ValueError(f"WBE {cost_element.wbe_id} not found")

    project = session.get(Project, wbe.project_id)
    if not project:
        raise ValueError(f"Project {wbe.project_id} not found")

    # Get schedule
    schedule_map = _get_schedule_map(session, [cost_element_id], control_date)
    schedule = schedule_map.get(cost_element_id)

    # Get earned value entry
    entry_map = _get_entry_map(session, [cost_element_id], control_date)
    entry = entry_map.get(cost_element_id)

    # Get cost registrations
    statement = select(CostRegistration).where(
        CostRegistration.cost_element_id == cost_element_id,
    )
    statement = apply_time_machine_filters(
        statement, TimeMachineEventType.COST_REGISTRATION, control_date
    )
    cost_registrations = session.exec(statement).all()

    # Calculate metrics
    metrics = get_cost_element_evm_metrics(
        cost_element=cost_element,
        schedule=schedule,
        entry=entry,
        cost_registrations=cost_registrations,
        control_date=control_date,
    )

    return {
        "context_type": "cost-element",
        "cost_element_id": str(cost_element.cost_element_id),
        "wbe_id": str(cost_element.wbe_id),
        "wbe_name": wbe.machine_type,
        "project_id": str(wbe.project_id),
        "project_name": project.project_name,
        "control_date": control_date.isoformat(),
        "planned_value": float(metrics.planned_value),
        "earned_value": float(metrics.earned_value),
        "actual_cost": float(metrics.actual_cost),
        "budget_bac": float(metrics.budget_bac),
        "cpi": float(metrics.cpi) if metrics.cpi else None,
        "spi": float(metrics.spi) if metrics.spi else None,
        "tcpi": (
            float(metrics.tcpi) if isinstance(metrics.tcpi, Decimal) else metrics.tcpi
        ),
        "cost_variance": float(metrics.cost_variance),
        "schedule_variance": float(metrics.schedule_variance),
    }


def _collect_baseline_metrics(
    session: Session, baseline_id: uuid.UUID, control_date: date
) -> dict:
    """Collect metrics for a baseline from BaselineCostElement records."""
    baseline = session.get(BaselineLog, baseline_id)
    if not baseline:
        raise ValueError(f"Baseline {baseline_id} not found")

    project = session.get(Project, baseline.project_id)
    if not project:
        raise ValueError(f"Project {baseline.project_id} not found")

    # Get all BaselineCostElement records for this baseline
    baseline_cost_elements = session.exec(
        select(BaselineCostElement).where(
            BaselineCostElement.baseline_id == baseline_id
        )
    ).all()

    if not baseline_cost_elements:
        # Return empty metrics
        return {
            "context_type": "baseline",
            "baseline_id": str(baseline.baseline_id),
            "baseline_date": baseline.baseline_date.isoformat(),
            "milestone_type": baseline.milestone_type,
            "project_id": str(baseline.project_id),
            "project_name": project.project_name,
            "control_date": control_date.isoformat(),
            "planned_value": Decimal("0.00"),
            "earned_value": Decimal("0.00"),
            "actual_cost": Decimal("0.00"),
            "budget_bac": Decimal("0.00"),
            "cost_element_count": 0,
        }

    # Aggregate from BaselineCostElement records
    total_planned_value = sum(bce.planned_value for bce in baseline_cost_elements)
    total_budget_bac = sum(bce.budget_bac for bce in baseline_cost_elements)
    total_revenue_plan = sum(bce.revenue_plan for bce in baseline_cost_elements)

    # Handle NULL values for optional fields
    actual_ac_values = [
        bce.actual_ac for bce in baseline_cost_elements if bce.actual_ac is not None
    ]
    total_actual_ac = sum(actual_ac_values) if actual_ac_values else Decimal("0.00")

    earned_ev_values = [
        bce.earned_ev for bce in baseline_cost_elements if bce.earned_ev is not None
    ]
    total_earned_ev = sum(earned_ev_values) if earned_ev_values else Decimal("0.00")

    forecast_eac_values = [
        bce.forecast_eac
        for bce in baseline_cost_elements
        if bce.forecast_eac is not None
    ]
    total_forecast_eac = sum(forecast_eac_values) if forecast_eac_values else None

    # Calculate indices from aggregated values
    cpi = (
        calculate_cpi(total_earned_ev, total_actual_ac) if total_actual_ac > 0 else None
    )
    spi = (
        calculate_spi(total_earned_ev, total_planned_value)
        if total_planned_value > 0
        else None
    )
    tcpi = (
        calculate_tcpi(total_budget_bac, total_earned_ev, total_actual_ac)
        if total_budget_bac > 0 and total_actual_ac > 0
        else None
    )
    cv = calculate_cost_variance(total_earned_ev, total_actual_ac)
    sv = calculate_schedule_variance(total_earned_ev, total_planned_value)

    return {
        "context_type": "baseline",
        "baseline_id": str(baseline.baseline_id),
        "baseline_date": baseline.baseline_date.isoformat(),
        "milestone_type": baseline.milestone_type,
        "description": baseline.description,
        "project_id": str(baseline.project_id),
        "project_name": project.project_name,
        "control_date": control_date.isoformat(),
        "planned_value": float(total_planned_value),
        "earned_value": float(total_earned_ev),
        "actual_cost": float(total_actual_ac),
        "budget_bac": float(total_budget_bac),
        "revenue_plan": float(total_revenue_plan),
        "forecast_eac": float(total_forecast_eac) if total_forecast_eac else None,
        "cpi": float(cpi) if cpi else None,
        "spi": float(spi) if spi else None,
        "tcpi": (float(tcpi) if isinstance(tcpi, Decimal) else tcpi),
        "cost_variance": float(cv),
        "schedule_variance": float(sv),
        "cost_element_count": len(baseline_cost_elements),
    }


def get_openai_config(session: Session, user_id: uuid.UUID) -> dict:
    """
    Get OpenAI configuration for a user, falling back to default app configuration.

    Priority:
    1. User's own configuration (if set)
    2. Default app configuration (if set and active)
    3. Error if neither is available

    Model configuration:
    - User model (user.openai_model) takes precedence over default model
    - Default model from AppConfiguration (ai_default_openai_model)
    - No autodetection - model must be explicitly configured

    Args:
        session: Database session
        user_id: User ID to get configuration for

    Returns:
        Dictionary with:
            - base_url: OpenAI API base URL
            - api_key: Decrypted OpenAI API key
            - model: Model name (from user config or default app config)
            - source: "user", "default", or "mixed" (user base_url + default api_key, or vice versa)

    Raises:
        ValueError: If no configuration is available or required fields are missing
    """
    user = session.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Get user config
    user_base_url = user.openai_base_url
    user_api_key_encrypted = user.openai_api_key_encrypted
    user_model = user.openai_model

    # Get default app config
    default_base_url_config = session.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key == "ai_default_openai_base_url",
            AppConfiguration.is_active,
        )
    ).first()

    default_api_key_config = session.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key == "ai_default_openai_api_key_encrypted",
            AppConfiguration.is_active,
        )
    ).first()

    default_model_config = session.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key == "ai_default_openai_model",
            AppConfiguration.is_active,
        )
    ).first()

    default_base_url = (
        default_base_url_config.config_value if default_base_url_config else None
    )
    default_api_key_encrypted = (
        default_api_key_config.config_value if default_api_key_config else None
    )
    default_model = default_model_config.config_value if default_model_config else None

    # Determine final base_url
    base_url = user_base_url if user_base_url else default_base_url

    # Determine final api_key
    api_key_encrypted = (
        user_api_key_encrypted if user_api_key_encrypted else default_api_key_encrypted
    )

    # Determine final model (user → default → error, NO autodetection)
    model = user_model if user_model else default_model

    # Validate that we have both base_url and api_key
    if not base_url:
        raise ValueError(
            "OpenAI base URL not found. Please configure base URL in user settings or default app configuration."
        )

    if not api_key_encrypted:
        raise ValueError(
            "OpenAI API key not found. Please configure API key in user settings or default app configuration."
        )

    # Validate that we have a model configured
    if not model:
        raise ValueError(
            "OpenAI model not found. Please configure model in user settings or default app configuration."
        )

    # Decrypt API key
    try:
        api_key = decrypt_api_key(api_key_encrypted)
    except ValueError as e:
        raise ValueError(f"Failed to decrypt OpenAI API key: {str(e)}") from e

    # Determine source
    if user_base_url and user_api_key_encrypted:
        source = "user"
    elif not user_base_url and not user_api_key_encrypted:
        source = "default"
    else:
        source = "mixed"

    return {
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "source": source,
    }


def create_chat_model(session: Session, user_id: uuid.UUID) -> ChatOpenAI:
    """
    Create a LangChain ChatOpenAI model instance with user configuration.

    Retrieves user OpenAI configuration (with defaults fallback) and creates
    a ChatOpenAI instance configured with base_url, api_key, and streaming enabled.

    Args:
        session: Database session
        user_id: User ID to get configuration for

    Returns:
        ChatOpenAI: Configured ChatOpenAI instance ready for use

    Raises:
        ValueError: If OpenAI configuration is not available or invalid
    """
    # Get OpenAI configuration for user
    config = get_openai_config(session=session, user_id=user_id)

    # Create ChatOpenAI instance with configuration
    chat_model = ChatOpenAI(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],  # Auto-detected from base URL
        temperature=0.7,  # Default temperature for balanced responses
        streaming=True,  # Enable streaming for progressive response generation
        max_tokens=None,  # No limit on tokens by default
        timeout=None,  # Use default timeout
        max_retries=2,  # Retry failed requests up to 2 times
    )

    return chat_model


class AssessmentState(TypedDict):
    """State for assessment generation workflow."""

    context_metrics: dict[str, Any]
    prompt: str
    assessment: str


class ChatState(TypedDict):
    """State for chat message workflow."""

    context_metrics: dict[str, Any]
    conversation_history: list[dict[str, Any]]
    user_message: str
    system_prompt: str
    response: str


def create_assessment_graph(
    session: Session,
    user_id: uuid.UUID,
) -> Any:  # Returns CompiledGraph from langgraph
    """
    Create LangGraph workflow for generating AI assessments with streaming support.

    Graph structure:
    - format_prompt: Formats context metrics into a prompt for the AI model
    - generate_assessment: Invokes chat model to generate assessment

    Args:
        session: Database session
        user_id: User ID to get OpenAI configuration for

    Returns:
        Compiled LangGraph graph ready for execution with streaming support

    Raises:
        ValueError: If OpenAI configuration is not available
    """
    # Get chat model for user
    chat_model = create_chat_model(session=session, user_id=user_id)

    def format_prompt(state: AssessmentState) -> dict[str, Any]:
        """Format context metrics into a prompt for assessment generation."""
        metrics = state["context_metrics"]
        context_type = metrics.get("context_type", "unknown")

        # Build prompt based on context type
        if context_type == "project":
            prompt_text = f"""Generate a comprehensive project assessment report in markdown format based on the following project metrics:

**Project Information:**
- Project: {metrics.get('project_name', 'Unknown')}
- Control Date: {metrics.get('control_date', 'N/A')}

**EVM Metrics:**
- Planned Value (PV): ${metrics.get('planned_value', 0):,.2f}
- Earned Value (EV): ${metrics.get('earned_value', 0):,.2f}
- Actual Cost (AC): ${metrics.get('actual_cost', 0):,.2f}
- Budget at Completion (BAC): ${metrics.get('budget_bac', 0):,.2f}
- Cost Performance Index (CPI): {metrics.get('cpi', 'N/A')}
- Schedule Performance Index (SPI): {metrics.get('spi', 'N/A')}
- To-Complete Performance Index (TCPI): {metrics.get('tcpi', 'N/A')}
- Cost Variance (CV): ${metrics.get('cost_variance', 0):,.2f}
- Schedule Variance (SV): ${metrics.get('schedule_variance', 0):,.2f}

Provide a detailed assessment including:
1. Overall project health status
2. Performance analysis (cost and schedule)
3. Key risks and issues
4. Recommendations for improvement
5. Forecast for project completion

Format the response in markdown with clear sections and bullet points."""
        elif context_type == "wbe":
            prompt_text = f"""Generate a comprehensive WBE (Work Breakdown Element) assessment report in markdown format based on the following metrics:

**WBE Information:**
- WBE: {metrics.get('wbe_name', 'Unknown')}
- Project: {metrics.get('project_name', 'Unknown')}
- Control Date: {metrics.get('control_date', 'N/A')}

**EVM Metrics:**
- Planned Value (PV): ${metrics.get('planned_value', 0):,.2f}
- Earned Value (EV): ${metrics.get('earned_value', 0):,.2f}
- Actual Cost (AC): ${metrics.get('actual_cost', 0):,.2f}
- Budget at Completion (BAC): ${metrics.get('budget_bac', 0):,.2f}
- Cost Performance Index (CPI): {metrics.get('cpi', 'N/A')}
- Schedule Performance Index (SPI): {metrics.get('spi', 'N/A')}

Provide a detailed assessment including performance analysis, risks, and recommendations."""
        elif context_type == "cost-element":
            prompt_text = f"""Generate a cost element assessment report in markdown format based on the following metrics:

**Cost Element Information:**
- Project: {metrics.get('project_name', 'Unknown')}
- WBE: {metrics.get('wbe_name', 'Unknown')}
- Control Date: {metrics.get('control_date', 'N/A')}

**EVM Metrics:**
- Planned Value (PV): ${metrics.get('planned_value', 0):,.2f}
- Earned Value (EV): ${metrics.get('earned_value', 0):,.2f}
- Actual Cost (AC): ${metrics.get('actual_cost', 0):,.2f}
- Budget at Completion (BAC): ${metrics.get('budget_bac', 0):,.2f}
- Cost Performance Index (CPI): {metrics.get('cpi', 'N/A')}
- Schedule Performance Index (SPI): {metrics.get('spi', 'N/A')}

Provide a detailed assessment including performance analysis, risks, and recommendations."""
        elif context_type == "baseline":
            prompt_text = f"""Generate a baseline assessment report in markdown format based on the following baseline snapshot:

**Baseline Information:**
- Baseline Date: {metrics.get('baseline_date', 'N/A')}
- Milestone: {metrics.get('milestone_type', 'Unknown')}
- Project: {metrics.get('project_name', 'Unknown')}
- Control Date: {metrics.get('control_date', 'N/A')}

**Baseline Metrics:**
- Planned Value: ${metrics.get('planned_value', 0):,.2f}
- Earned Value: ${metrics.get('earned_value', 0):,.2f}
- Actual Cost: ${metrics.get('actual_cost', 0):,.2f}
- Budget at Completion (BAC): ${metrics.get('budget_bac', 0):,.2f}
- Cost Performance Index (CPI): {metrics.get('cpi', 'N/A')}
- Schedule Performance Index (SPI): {metrics.get('spi', 'N/A')}

Provide a detailed assessment of the baseline snapshot."""
        else:
            prompt_text = f"""Generate an assessment report in markdown format based on the following metrics:

{metrics}

Provide a detailed assessment including performance analysis, risks, and recommendations."""

        return {"prompt": prompt_text}

    def generate_assessment(state: AssessmentState) -> dict[str, Any]:
        """Generate assessment using chat model."""
        prompt_text = state["prompt"]

        # Create prompt template
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert project management analyst. Provide detailed, actionable assessments based on EVM metrics. Always format your responses in markdown.",
                ),
                ("human", "{input}"),
            ]
        )

        # Create chain with streaming support
        chain = prompt | chat_model

        # Invoke chain to generate assessment
        # For streaming, we'll handle it in the calling code
        response = chain.invoke({"input": prompt_text})

        # Extract assessment text
        assessment_text = (
            response.content if hasattr(response, "content") else str(response)
        )

        return {"assessment": assessment_text}

    # Build graph
    workflow = StateGraph(AssessmentState)
    workflow.add_node("format_prompt", format_prompt)
    workflow.add_node("generate_assessment", generate_assessment)

    # Define edges
    workflow.add_edge(START, "format_prompt")
    workflow.add_edge("format_prompt", "generate_assessment")

    # Compile graph
    graph = workflow.compile()

    return graph


async def generate_initial_assessment(
    session: Session,
    user_id: uuid.UUID,
    context_type: ContextType,
    context_id: uuid.UUID,
    control_date: date,
    send_message: Callable[
        [dict[str, Any]], Awaitable[None]
    ],  # WebSocket send function (async)
) -> None:
    """
    Generate initial AI assessment with WebSocket streaming support.

    Collects context metrics, formats prompt, and streams the assessment
    response token-by-token via WebSocket.

    Args:
        session: Database session
        user_id: User ID to get OpenAI configuration for
        context_type: Type of context (project, wbe, cost-element, baseline)
        context_id: ID of the context entity
        control_date: Control date for time-machine filtering
        send_message: Callable function to send messages (e.g., WebSocket.send_json)
                      Should accept a dict with 'type' and 'content' keys

    Raises:
        ValueError: If OpenAI configuration is not available or context not found
        Exception: Any errors during streaming (sent via WebSocket before raising)
    """
    try:
        # Collect context metrics
        context_metrics = collect_context_metrics(
            session=session,
            context_type=context_type,
            context_id=context_id,
            control_date=control_date,
        )

        # Format prompt using the prompt formatting logic from the graph
        context_type_str = context_metrics.get("context_type", "unknown")
        if context_type_str == "project":
            prompt_text = f"""Generate a comprehensive project assessment report in markdown format based on the following project metrics:

**Project Information:**
- Project: {context_metrics.get('project_name', 'Unknown')}
- Control Date: {context_metrics.get('control_date', 'N/A')}

**EVM Metrics:**
- Planned Value (PV): ${context_metrics.get('planned_value', 0):,.2f}
- Earned Value (EV): ${context_metrics.get('earned_value', 0):,.2f}
- Actual Cost (AC): ${context_metrics.get('actual_cost', 0):,.2f}
- Budget at Completion (BAC): ${context_metrics.get('budget_bac', 0):,.2f}
- Cost Performance Index (CPI): {context_metrics.get('cpi', 'N/A')}
- Schedule Performance Index (SPI): {context_metrics.get('spi', 'N/A')}
- To-Complete Performance Index (TCPI): {context_metrics.get('tcpi', 'N/A')}
- Cost Variance (CV): ${context_metrics.get('cost_variance', 0):,.2f}
- Schedule Variance (SV): ${context_metrics.get('schedule_variance', 0):,.2f}

Provide a detailed assessment including:
1. Overall project health status
2. Performance analysis (cost and schedule)
3. Key risks and issues
4. Recommendations for improvement
5. Forecast for project completion

Format the response in markdown with clear sections and bullet points."""
        elif context_type_str == "wbe":
            prompt_text = f"""Generate a comprehensive WBE (Work Breakdown Element) assessment report in markdown format based on the following metrics:

**WBE Information:**
- WBE: {context_metrics.get('wbe_name', 'Unknown')}
- Project: {context_metrics.get('project_name', 'Unknown')}
- Control Date: {context_metrics.get('control_date', 'N/A')}

**EVM Metrics:**
- Planned Value (PV): ${context_metrics.get('planned_value', 0):,.2f}
- Earned Value (EV): ${context_metrics.get('earned_value', 0):,.2f}
- Actual Cost (AC): ${context_metrics.get('actual_cost', 0):,.2f}
- Budget at Completion (BAC): ${context_metrics.get('budget_bac', 0):,.2f}
- Cost Performance Index (CPI): {context_metrics.get('cpi', 'N/A')}
- Schedule Performance Index (SPI): {context_metrics.get('spi', 'N/A')}

Provide a detailed assessment including performance analysis, risks, and recommendations."""
        elif context_type_str == "cost-element":
            prompt_text = f"""Generate a cost element assessment report in markdown format based on the following metrics:

**Cost Element Information:**
- Project: {context_metrics.get('project_name', 'Unknown')}
- WBE: {context_metrics.get('wbe_name', 'Unknown')}
- Control Date: {context_metrics.get('control_date', 'N/A')}

**EVM Metrics:**
- Planned Value (PV): ${context_metrics.get('planned_value', 0):,.2f}
- Earned Value (EV): ${context_metrics.get('earned_value', 0):,.2f}
- Actual Cost (AC): ${context_metrics.get('actual_cost', 0):,.2f}
- Budget at Completion (BAC): ${context_metrics.get('budget_bac', 0):,.2f}
- Cost Performance Index (CPI): {context_metrics.get('cpi', 'N/A')}
- Schedule Performance Index (SPI): {context_metrics.get('spi', 'N/A')}

Provide a detailed assessment including performance analysis, risks, and recommendations."""
        elif context_type_str == "baseline":
            prompt_text = f"""Generate a baseline assessment report in markdown format based on the following baseline snapshot:

**Baseline Information:**
- Baseline Date: {context_metrics.get('baseline_date', 'N/A')}
- Milestone: {context_metrics.get('milestone_type', 'Unknown')}
- Project: {context_metrics.get('project_name', 'Unknown')}
- Control Date: {context_metrics.get('control_date', 'N/A')}

**Baseline Metrics:**
- Planned Value: ${context_metrics.get('planned_value', 0):,.2f}
- Earned Value: ${context_metrics.get('earned_value', 0):,.2f}
- Actual Cost: ${context_metrics.get('actual_cost', 0):,.2f}
- Budget at Completion (BAC): ${context_metrics.get('budget_bac', 0):,.2f}
- Cost Performance Index (CPI): {context_metrics.get('cpi', 'N/A')}
- Schedule Performance Index (SPI): {context_metrics.get('spi', 'N/A')}

Provide a detailed assessment of the baseline snapshot."""
        else:
            prompt_text = f"""Generate an assessment report in markdown format based on the following metrics:

{context_metrics}

Provide a detailed assessment including performance analysis, risks, and recommendations."""

        # Create chat model for streaming
        chat_model = create_chat_model(session=session, user_id=user_id)

        # Create prompt template
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert project management analyst. Provide detailed, actionable assessments based on EVM metrics. Always format your responses in markdown.",
                ),
                ("human", "{input}"),
            ]
        )

        # Create chain with streaming support
        chain = prompt | chat_model

        # Stream tokens directly from the chain
        async for chunk in chain.astream({"input": prompt_text}):
            # Extract content from chunk (chunk is an AIMessageChunk)
            if hasattr(chunk, "content"):
                content = chunk.content
                if content:
                    # Send each token chunk via WebSocket
                    await send_message(
                        {
                            "type": "assessment_chunk",
                            "content": content,
                        }
                    )

        # Send completion message
        await send_message(
            {
                "type": "assessment_complete",
                "content": "",
            }
        )

    except ValueError as e:
        # Send error via WebSocket
        await send_message(
            {
                "type": "error",
                "content": str(e),
            }
        )
        raise
    except Exception as e:
        # Send generic error via WebSocket
        await send_message(
            {
                "type": "error",
                "content": f"An error occurred: {str(e)}",
            }
        )
        raise


def create_chat_graph(
    session: Session,
    user_id: uuid.UUID,
) -> Any:  # Returns CompiledGraph from langgraph
    """
    Create LangGraph workflow for chat messages with conversation history.

    Graph structure:
    - format_chat_prompt: Formats conversation history and context metrics into a prompt
    - generate_response: Invokes chat model to generate response

    Args:
        session: Database session
        user_id: User ID to get OpenAI configuration for

    Returns:
        Compiled LangGraph graph ready for execution with streaming support

    Raises:
        ValueError: If OpenAI configuration is not available
    """
    # Get chat model for user
    chat_model = create_chat_model(session=session, user_id=user_id)

    def format_chat_prompt(state: ChatState) -> dict[str, Any]:
        """Format conversation history and context metrics into a prompt."""
        context_metrics = state["context_metrics"]
        # conversation_history and user_message are used in generate_response, not here
        _conversation_history = state["conversation_history"]
        _user_message = state["user_message"]
        del _conversation_history, _user_message  # Suppress linting warnings

        context_type = context_metrics.get("context_type", "unknown")

        # Build system prompt with context information
        if context_type == "project":
            system_prompt = f"""You are an expert project management analyst. The user is asking about the following project:

**Project Information:**
- Project: {context_metrics.get('project_name', 'Unknown')}
- Control Date: {context_metrics.get('control_date', 'N/A')}

**Current EVM Metrics:**
- Planned Value (PV): ${context_metrics.get('planned_value', 0):,.2f}
- Earned Value (EV): ${context_metrics.get('earned_value', 0):,.2f}
- Actual Cost (AC): ${context_metrics.get('actual_cost', 0):,.2f}
- Budget at Completion (BAC): ${context_metrics.get('budget_bac', 0):,.2f}
- Cost Performance Index (CPI): {context_metrics.get('cpi', 'N/A')}
- Schedule Performance Index (SPI): {context_metrics.get('spi', 'N/A')}

Provide helpful, actionable answers based on these metrics. Always format your responses in markdown."""
        elif context_type == "wbe":
            system_prompt = f"""You are an expert project management analyst. The user is asking about the following WBE:

**WBE Information:**
- WBE: {context_metrics.get('wbe_name', 'Unknown')}
- Project: {context_metrics.get('project_name', 'Unknown')}
- Control Date: {context_metrics.get('control_date', 'N/A')}

**Current EVM Metrics:**
- Planned Value (PV): ${context_metrics.get('planned_value', 0):,.2f}
- Earned Value (EV): ${context_metrics.get('earned_value', 0):,.2f}
- Actual Cost (AC): ${context_metrics.get('actual_cost', 0):,.2f}

Provide helpful, actionable answers based on these metrics. Always format your responses in markdown."""
        elif context_type == "cost-element":
            system_prompt = f"""You are an expert project management analyst. The user is asking about the following cost element:

**Cost Element Information:**
- Project: {context_metrics.get('project_name', 'Unknown')}
- WBE: {context_metrics.get('wbe_name', 'Unknown')}
- Control Date: {context_metrics.get('control_date', 'N/A')}

**Current EVM Metrics:**
- Planned Value (PV): ${context_metrics.get('planned_value', 0):,.2f}
- Earned Value (EV): ${context_metrics.get('earned_value', 0):,.2f}
- Actual Cost (AC): {context_metrics.get('actual_cost', 0):,.2f}

Provide helpful, actionable answers based on these metrics. Always format your responses in markdown."""
        elif context_type == "baseline":
            system_prompt = f"""You are an expert project management analyst. The user is asking about the following baseline:

**Baseline Information:**
- Baseline Date: {context_metrics.get('baseline_date', 'N/A')}
- Milestone: {context_metrics.get('milestone_type', 'Unknown')}
- Project: {context_metrics.get('project_name', 'Unknown')}

Provide helpful, actionable answers based on the baseline snapshot. Always format your responses in markdown."""
        else:
            system_prompt = "You are an expert project management analyst. Provide helpful, actionable answers. Always format your responses in markdown."

        return {"system_prompt": system_prompt}

    def generate_response(state: ChatState) -> dict[str, Any]:
        """Generate response using chat model with conversation history."""
        conversation_history = state["conversation_history"]
        user_message = state["user_message"]
        system_prompt = state["system_prompt"]

        # Build messages for chat model
        messages = [("system", system_prompt)]

        # Add conversation history
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                messages.append(("human", content))
            elif role == "assistant":
                messages.append(("ai", content))

        # Add current user message
        messages.append(("human", user_message))

        # Create prompt template
        prompt = ChatPromptTemplate.from_messages(messages)

        # Create chain with streaming support
        chain = prompt | chat_model

        # Invoke chain to generate response
        response = chain.invoke({})

        # Extract response text
        response_text = (
            response.content if hasattr(response, "content") else str(response)
        )

        return {"response": response_text}

    # Build graph
    workflow = StateGraph(ChatState)
    workflow.add_node("format_chat_prompt", format_chat_prompt)
    workflow.add_node("generate_response", generate_response)

    # Define edges
    workflow.add_edge(START, "format_chat_prompt")
    workflow.add_edge("format_chat_prompt", "generate_response")

    # Compile graph
    graph = workflow.compile()

    return graph


async def send_chat_message(
    session: Session,
    user_id: uuid.UUID,
    context_type: ContextType,
    context_id: uuid.UUID,
    control_date: date,
    message: str,
    conversation_history: list[dict[str, Any]],
    send_message: Callable[
        [dict[str, Any]], Awaitable[None]
    ],  # WebSocket send function (async)
) -> None:
    """
    Handle chat message with conversation history and WebSocket streaming support.

    Collects context metrics, formats system prompt with conversation history, and streams
    the AI response token-by-token via WebSocket.

    Args:
        session: Database session
        user_id: User ID to get OpenAI configuration for
        context_type: Type of context (project, wbe, cost-element, baseline)
        context_id: ID of the context entity
        control_date: Control date for time-machine filtering
        message: User's chat message
        conversation_history: List of previous messages in format [{"role": "user|assistant", "content": "..."}]
        send_message: Callable function to send messages (e.g., WebSocket.send_json)
                      Should accept a dict with 'type' and 'content' keys

    Raises:
        ValueError: If OpenAI configuration is not available or context not found
        Exception: Any errors during streaming (sent via WebSocket before raising)
    """
    try:
        # Collect context metrics
        context_metrics = collect_context_metrics(
            session=session,
            context_type=context_type,
            context_id=context_id,
            control_date=control_date,
        )

        # Format system prompt based on context type
        context_type_str = context_metrics.get("context_type", "unknown")
        if context_type_str == "project":
            system_prompt = f"""You are an expert project management analyst. The user is asking about the following project:

**Project Information:**
- Project: {context_metrics.get('project_name', 'Unknown')}
- Control Date: {context_metrics.get('control_date', 'N/A')}

**Current EVM Metrics:**
- Planned Value (PV): ${context_metrics.get('planned_value', 0):,.2f}
- Earned Value (EV): ${context_metrics.get('earned_value', 0):,.2f}
- Actual Cost (AC): ${context_metrics.get('actual_cost', 0):,.2f}
- Budget at Completion (BAC): ${context_metrics.get('budget_bac', 0):,.2f}
- Cost Performance Index (CPI): {context_metrics.get('cpi', 'N/A')}
- Schedule Performance Index (SPI): {context_metrics.get('spi', 'N/A')}

Provide helpful, actionable answers based on these metrics. Always format your responses in markdown."""
        elif context_type_str == "wbe":
            system_prompt = f"""You are an expert project management analyst. The user is asking about the following WBE:

**WBE Information:**
- WBE: {context_metrics.get('wbe_name', 'Unknown')}
- Project: {context_metrics.get('project_name', 'Unknown')}
- Control Date: {context_metrics.get('control_date', 'N/A')}

**Current EVM Metrics:**
- Planned Value (PV): ${context_metrics.get('planned_value', 0):,.2f}
- Earned Value (EV): ${context_metrics.get('earned_value', 0):,.2f}
- Actual Cost (AC): ${context_metrics.get('actual_cost', 0):,.2f}

Provide helpful, actionable answers based on these metrics. Always format your responses in markdown."""
        elif context_type_str == "cost-element":
            system_prompt = f"""You are an expert project management analyst. The user is asking about the following cost element:

**Cost Element Information:**
- Project: {context_metrics.get('project_name', 'Unknown')}
- WBE: {context_metrics.get('wbe_name', 'Unknown')}
- Control Date: {context_metrics.get('control_date', 'N/A')}

**Current EVM Metrics:**
- Planned Value (PV): ${context_metrics.get('planned_value', 0):,.2f}
- Earned Value (EV): ${context_metrics.get('earned_value', 0):,.2f}
- Actual Cost (AC): {context_metrics.get('actual_cost', 0):,.2f}

Provide helpful, actionable answers based on these metrics. Always format your responses in markdown."""
        elif context_type_str == "baseline":
            system_prompt = f"""You are an expert project management analyst. The user is asking about the following baseline:

**Baseline Information:**
- Baseline Date: {context_metrics.get('baseline_date', 'N/A')}
- Milestone: {context_metrics.get('milestone_type', 'Unknown')}
- Project: {context_metrics.get('project_name', 'Unknown')}

Provide helpful, actionable answers based on the baseline snapshot. Always format your responses in markdown."""
        else:
            system_prompt = "You are an expert project management analyst. Provide helpful, actionable answers. Always format your responses in markdown."

        # Build messages for chat model
        messages = [("system", system_prompt)]

        # Add conversation history
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                messages.append(("human", content))
            elif role == "assistant":
                messages.append(("ai", content))

        # Add current user message
        messages.append(("human", message))

        # Create chat model for streaming
        chat_model = create_chat_model(session=session, user_id=user_id)

        # Create prompt template
        prompt = ChatPromptTemplate.from_messages(messages)

        # Create chain with streaming support
        chain = prompt | chat_model

        # Stream tokens directly from the chain
        async for chunk in chain.astream({}):
            # Extract content from chunk (chunk is an AIMessageChunk)
            if hasattr(chunk, "content"):
                content = chunk.content
                if content:
                    # Send each token chunk via WebSocket
                    await send_message(
                        {
                            "type": "response_chunk",
                            "content": content,
                        }
                    )

        # Send completion message
        await send_message(
            {
                "type": "response_complete",
                "content": "",
            }
        )

    except ValueError as e:
        # Send error via WebSocket
        await send_message(
            {
                "type": "error",
                "content": str(e),
            }
        )
        raise
    except Exception as e:
        # Send generic error via WebSocket
        await send_message(
            {
                "type": "error",
                "content": f"An error occurred: {str(e)}",
            }
        )
        raise
