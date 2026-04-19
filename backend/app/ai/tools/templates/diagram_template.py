"""Diagram tool template for generating Mermaid diagrams.

This template provides AI tools for creating various types of diagrams
using Mermaid syntax. The AI can generate diagrams from natural language
descriptions.

Supported diagram types:
- Flowchart: Process flows, decision trees
- Sequence: Interactions between actors/components
- Class: UML class diagrams
- State: State machine diagrams
- ER: Entity relationship diagrams
- Gantt: Project timelines
"""

import logging
from typing import Annotated, Any

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import RiskLevel, ToolContext

logger = logging.getLogger(__name__)


# =============================================================================
# MERMAID DIAGRAM TOOLS
# =============================================================================


@ai_tool(
    name="generate_mermaid_diagram",
    description="Generate a Mermaid diagram from a description. "
    "Supports flowchart, sequence, class, state, ER, and Gantt diagrams. "
    "Returns Mermaid code that can be rendered in compatible viewers.",
    permissions=["ai-chat"],
    category="diagrams",
    risk_level=RiskLevel.LOW,
)
async def generate_mermaid_diagram(
    diagram_type: str,
    description: str,
    title: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Generate a Mermaid diagram from natural language description.

    Context: Provides session context for the AI chat.

    Args:
        diagram_type: Type of diagram (flowchart, sequence, class, state, er, gantt)
        description: Natural language description of what the diagram should show
        title: Optional title for the diagram
        context: Injected tool execution context

    Returns:
        Dictionary with:
        - mermaid_code: Mermaid syntax code
        - diagram_type: The type of diagram generated
        - title: Diagram title
        - render_url: URL to render the diagram (using Mermaid live editor)

    Raises:
        ValueError: If diagram_type is not supported

    Example:
        >>> result = await generate_mermaid_diagram(
        ...     diagram_type="flowchart",
        ...     description="User login process with authentication",
        ...     title="Login Flow"
        ... )
        >>> print(result['mermaid_code'])
    """
    try:
        # Normalize diagram type
        diagram_type = diagram_type.lower()
        supported_types = ["flowchart", "sequence", "class", "state", "er", "gantt"]

        if diagram_type not in supported_types:
            return {
                "error": f"Unsupported diagram type: {diagram_type}. "
                f"Supported types: {', '.join(supported_types)}"
            }

        # Generate Mermaid code based on type and description
        mermaid_code = _generate_diagram_code(diagram_type, description)

        # Create render URL (using Mermaid live editor for preview)
        encoded_code = mermaid_code.replace("\n", "%0A")
        render_url = f"https://mermaid.live/edit#base64:{encoded_code}"

        return {
            "mermaid_code": mermaid_code,
            "diagram_type": diagram_type,
            "title": title or f"{diagram_type.title()} Diagram",
            "render_url": render_url,
            "description": description,
        }
    except Exception as e:
        logger.error(f"Error generating Mermaid diagram: {e}")
        return {"error": str(e)}


def _generate_diagram_code(diagram_type: str, description: str) -> str:
    """Generate Mermaid code based on diagram type and description.

    Args:
        diagram_type: Type of diagram to generate
        description: Natural language description

    Returns:
        Mermaid syntax code string
    """
    # This is a simplified implementation
    # In production, you would use AI/LLM to generate the actual diagram
    # based on the natural language description

    if diagram_type == "flowchart":
        return _generate_flowchart(description)
    elif diagram_type == "sequence":
        return _generate_sequence_diagram(description)
    elif diagram_type == "class":
        return _generate_class_diagram(description)
    elif diagram_type == "state":
        return _generate_state_diagram(description)
    elif diagram_type == "er":
        return _generate_er_diagram(description)
    elif diagram_type == "gantt":
        return _generate_gantt_diagram(description)
    else:
        return f"%% Unsupported diagram type: {diagram_type}"


def _generate_flowchart(description: str) -> str:
    """Generate a flowchart from description.

    For production, this would use an LLM to parse the description
    and generate appropriate Mermaid flowchart syntax.
    """
    # Simplified template-based generation
    # Extract key entities from description (basic keyword matching)
    desc_lower = description.lower()

    # Determine flowchart direction
    direction = "TD"  # Top-Down default
    if "left" in desc_lower or "horizontal" in desc_lower:
        direction = "LR"

    # Build nodes based on description
    nodes = []
    edges = []

    # Common patterns
    if "login" in desc_lower or "authentication" in desc_lower:
        nodes.extend(
            [
                "A[Start]",
                "B{Is user logged in?}",
                "C[Show login form]",
                "D[Authenticate credentials]",
                "E[Grant access]",
                "F[Deny access]",
            ]
        )
        edges.extend(
            [
                "A --> B",
                "B -- No --> C",
                "C --> D",
                "D -- Valid --> E",
                "D -- Invalid --> F",
                "B -- Yes --> E",
            ]
        )
    elif "approval" in desc_lower:
        nodes.extend(
            [
                "A[Start]",
                "B{Is approved?}",
                "C[Request changes]",
                "D[Proceed with work]",
                "E[End]",
            ]
        )
        edges.extend(
            ["A --> B", "B -- No --> C", "C --> B", "B -- Yes --> D", "D --> E"]
        )
    else:
        # Generic flowchart
        nodes = [
            "A[Start]",
            "B[Process Step 1]",
            "C[Process Step 2]",
            "D[Decision Point]",
            "E[End]",
        ]
        edges = ["A --> B", "B --> C", "C --> D", "D --> E"]

    # Build Mermaid code
    code = f"flowchart {direction}\n"
    for node in nodes:
        code += f"    {node}\n"
    for edge in edges:
        code += f"    {edge}\n"

    return code


def _generate_sequence_diagram(description: str) -> str:
    """Generate a sequence diagram from description."""
    desc_lower = description.lower()

    # Default actors
    actors = ["User", "System"]

    # Add relevant actors based on description
    if "api" in desc_lower:
        actors.append("API")
    if "database" in desc_lower or "db" in desc_lower:
        actors.append("Database")
    if "auth" in desc_lower:
        actors.append("AuthService")

    # Build sequence
    code = "sequenceDiagram\n"
    for actor in actors:
        code += f"    actor {actor}\n"

    # Generate messages based on description
    if "login" in desc_lower or "authentication" in desc_lower:
        code += """
    User->>AuthService: Login Request
    AuthService->>Database: Validate Credentials
    Database-->>AuthService: User Data
    AuthService-->>User: Auth Token
    User->>System: Access Request
    System-->>User: Granted Access
"""
    elif "api" in desc_lower:
        code += """
    User->>API: HTTP Request
    API->>Database: Query Data
    Database-->>API: Result Set
    API-->>User: JSON Response
"""
    else:
        code += """
    User->>System: Request
    System->>System: Process
    System-->>User: Response
"""

    return code


def _generate_class_diagram(description: str) -> str:
    """Generate a UML class diagram from description."""
    desc_lower = description.lower()

    code = "classDiagram\n"

    # Generate classes based on description
    if "user" in desc_lower:
        code += """
    class User {
        +String user_id
        +String email
        +String full_name
        +login()
        +logout()
    }
"""

    if "project" in desc_lower:
        code += """
    class Project {
        +String project_id
        +String name
        +String code
        +Float budget
        +createWBE()
        +getMetrics()
    }
"""

    if "wbe" in desc_lower or "work breakdown" in desc_lower:
        code += """
    class WBE {
        +String wbe_id
        +String name
        +String code
        +Float budget
        +getCostElements()
    }
"""

    # Add relationships
    if "project" in desc_lower and (
        "wbe" in desc_lower or "work breakdown" in desc_lower
    ):
        code += '    Project "1" -- "*" WBE : contains\n'

    if "user" in desc_lower and "project" in desc_lower:
        code += '    User "1" -- "*" Project : manages\n'

    return code


def _generate_state_diagram(description: str) -> str:
    """Generate a state diagram from description."""
    desc_lower = description.lower()

    code = "stateDiagram-v2\n"

    if "order" in desc_lower or "workflow" in desc_lower:
        code += """
    [*] --> Draft
    Draft --> Submitted: Submit
    Submitted --> Approved: Approve
    Submitted --> Rejected: Reject
    Rejected --> Draft: Revise
    Approved --> Implemented: Implement
    Implemented --> [*]
"""
    elif "task" in desc_lower:
        code += """
    [*] --> Pending
    Pending --> InProgress: Start
    InProgress --> Completed: Finish
    InProgress --> Blocked: Block
    Blocked --> InProgress: Unblock
    Completed --> [*]
"""
    else:
        code += """
    [*] --> State1
    State1 --> State2: Event
    State2 --> [*]
"""

    return code


def _generate_er_diagram(description: str) -> str:
    """Generate an entity relationship diagram from description."""
    desc_lower = description.lower()

    code = "erDiagram\n"

    # Common entities
    if "project" in desc_lower:
        code += "    PROJECT {\n        string project_id PK\n        string name\n        string code\n        float budget\n    }\n"

    if "wbe" in desc_lower or "work breakdown" in desc_lower:
        code += "    WBE {\n        string wbe_id PK\n        string name\n        string code\n        float budget\n        string project_id FK\n    }\n"

    if "cost" in desc_lower and "element" in desc_lower:
        code += "    COST_ELEMENT {\n        string cost_element_id PK\n        string name\n        string code\n        float budget_amount\n        string wbe_id FK\n    }\n"

    if "user" in desc_lower:
        code += "    USER {\n        string user_id PK\n        string email\n        string full_name\n        string role\n    }\n"

    # Add relationships
    if "project" in desc_lower and "wbe" in desc_lower:
        code += "    PROJECT ||--o{ WBE : contains\n"

    if "wbe" in desc_lower and "cost" in desc_lower:
        code += "    WBE ||--o{ COST_ELEMENT : contains\n"

    if "user" in desc_lower and "project" in desc_lower:
        code += "    USER ||--o{ PROJECT : manages\n"

    return code


def _generate_gantt_diagram(description: str) -> str:
    """Generate a Gantt chart from description."""
    desc_lower = description.lower()

    # Extract project duration from description
    days = 30  # default
    for word in desc_lower.split():
        if word.isdigit():
            days = int(word)
            if days > 365:  # Assume months if too large
                days = 30
            break

    code = f"gantt\n    title {description[:50]}\n    dateFormat YYYY-MM-DD\n"

    # Generate sections based on description
    if "phase" in desc_lower:
        code += """
    section Phase 1
    Planning           :a1, 2024-01-01, 7d
    Requirements      :a2, after a1, 5d

    section Phase 2
    Development        :b1, after a2, 14d
    Testing            :b2, after b1, 7d

    section Phase 3
    Deployment         :c1, after b2, 3d
"""
    else:
        code += """
    section Planning
    Requirements       :done, p1, 2024-01-01, 5d
    Design             :done, p2, after p1, 7d

    section Development
    Frontend           :active, d1, 2024-01-13, 14d
    Backend            :d2, after d1, 10d

    section Testing
    Integration        :t1, after d2, 7d
    UAT                :t2, after t1, 5d
"""

    return code


# =============================================================================
# TEMPLATE USAGE NOTES
# =============================================================================

"""
MERMAID DIAGRAM TOOL PATTERNS:

1. DIAGRAM TYPES:
   - flowchart: Process flows, decision trees, workflows
   - sequence: Interactions between actors/components over time
   - class: UML class diagrams showing structure and relationships
   - state: State machine diagrams showing state transitions
   - er: Entity relationship diagrams for database schema
   - gantt: Project timelines and schedules

2. GENERATION APPROACH:
   - Current implementation uses template-based generation
   - Production implementation should use LLM for parsing
   - LLM can extract entities and relationships from description
   - Generate more accurate and context-aware diagrams

3. RENDERING OPTIONS:
   - Mermaid live editor: https://mermaid.live
   - Mermaid CLI for image generation
   - Frontend libraries: mermaid.js, react-mermaid
   - Static image generation via CLI

4. FRONTEND INTEGRATION:
   - Store mermaid_code in message content
   - Use content_format: "mermaid"
   - Frontend renders using mermaid.js
   - Support export to PNG/SVG

5. EXAMPLE USAGE:
   User: "Create a flowchart showing the change order approval process"
   AI: Generates Mermaid flowchart code

   User: "Show me the entity relationships for projects"
   AI: Generates ER diagram

BEST PRACTICES:
   - Keep diagrams simple and readable
   - Use consistent naming conventions
   - Add labels to relationships
   - Limit complexity for better rendering
   - Provide descriptive titles

ENHANCEMENTS:
   - Add LLM-based diagram generation
   - Support subgraphs and nested diagrams
   - Add styling and theming options
   - Generate diagrams from existing data
   - Support mind maps and network diagrams
"""
