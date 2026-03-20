"""AI-powered Change Order requirement parser.

This module uses LLM to extract structured information from natural language
change order requirements and generate comprehensive draft change orders.

Integrates with ImpactAnalysisService to provide accurate impact assessments.
"""

import json
import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import LLMClientFactory
from app.services.ai_config_service import AIConfigService
from app.services.impact_analysis_service import ImpactAnalysisService

logger = logging.getLogger(__name__)


class ChangeOrderRequirementParser:
    """Parse natural language requirements into structured change order data.

    Uses LLM to extract:
    - Title and description
    - Business reason/justification
    - Estimated costs and budget impact
    - Timeline/schedule impacts
    - Risk factors and affected entities

    Attributes:
        session: Database session for accessing AI config
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the parser with database session.

        Args:
            session: Async database session for AI config access
        """
        self.session = session
        self._config_service = AIConfigService(session)
        self._impact_service = ImpactAnalysisService(session)

    async def _get_llm_client(self) -> AsyncOpenAI:
        """Get configured LLM client for parsing.

        Returns:
            Configured AsyncOpenAI client

        Raises:
            ValueError: If no AI provider is configured
        """
        # Get first available provider
        providers = await self._config_service.list_providers()
        if not providers:
            raise ValueError("No AI provider configured")

        # Use first available provider
        provider = providers[0]
        return await LLMClientFactory.create_client(provider, self._config_service)

    async def _get_model_name(self) -> str:
        """Get the model name to use for parsing.

        Returns:
            Model identifier string

        Raises:
            ValueError: If no AI model is configured
        """
        providers = await self._config_service.list_providers()
        if not providers:
            raise ValueError("No AI provider configured")

        provider = providers[0]
        models = await self._config_service.list_models(provider_id=provider.id)
        if not models:
            raise ValueError("No AI model configured for provider")

        # Use first available model
        return str(models[0].model_id)

    async def parse_requirements(
        self,
        project_id: UUID,
        title: str,
        description: str,
        reason: str,
    ) -> dict[str, Any]:
        """Parse natural language requirements into structured change order data.

        Analyzes the input requirements and extracts:
        - Refined title and description
        - Business justification
        - Budget impact estimate
        - Schedule impact (days)
        - Risk level (Low/Medium/High)
        - Affected entities (WBEs, Cost Elements)
        - Recommendations

        Args:
            project_id: UUID of the project
            title: Initial change order title
            description: Detailed description of the change
            reason: Business reason for the change

        Returns:
            Dictionary with parsed change order data including:
            - title: Refined title
            - description: Enhanced description
            - reason: Business justification
            - budget_impact: Estimated budget impact (Decimal)
            - schedule_impact_days: Estimated schedule impact in days
            - risk_level: Risk assessment (Low/Medium/High)
            - affected_entities: List of affected entity identifiers
            - recommendation: Approval recommendation
            - confidence_score: Confidence in the analysis (0.0-1.0)

        Raises:
            ValueError: If AI provider is not configured or parsing fails
        """
        try:
            client = await self._get_llm_client()
            model_name = await self._get_model_name()

            # Build the parsing prompt
            system_prompt = """You are an expert project management analyst specializing in change order analysis for industrial automation projects.

Your task is to analyze change order requirements and extract structured information.

Extract the following fields:
1. title: A clear, concise title (max 100 chars)
2. description: Enhanced description with technical details (max 500 chars)
3. reason: Professional business justification (max 300 chars)
4. budget_impact: Estimated cost impact in EUR (positive = increase, negative = decrease)
5. schedule_impact_days: Estimated delay in days (integer, can be 0)
6. risk_level: One of "Low", "Medium", or "High"
7. affected_entities: List of potentially affected work breakdown elements or cost elements (e.g., ["WBE-001", "CE-002"])
8. recommendation: One of "Approve", "Approve with conditions", "Review required", or "Reject"
9. confidence_score: Your confidence in this analysis (0.0 to 1.0)

Consider:
- Technical complexity
- Resource requirements
- Schedule dependencies
- Risk factors
- Project context

Respond ONLY with valid JSON, no additional text."""

            user_prompt = f"""Analyze this change order request:

Project ID: {project_id}
Title: {title}
Description: {description}
Reason: {reason}

Provide structured analysis as JSON."""

            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # Lower temperature for more consistent parsing
                max_tokens=1000,
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from LLM")

            # Parse JSON response
            try:
                parsed_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {content}")
                raise ValueError(f"Invalid JSON response from LLM: {e}") from e

            # Validate and convert fields
            result = {
                "title": str(parsed_data.get("title", title))[:200],
                "description": str(parsed_data.get("description", description))[:1000],
                "reason": str(parsed_data.get("reason", reason))[:500],
                "budget_impact": Decimal(str(parsed_data.get("budget_impact", 0))),
                "schedule_impact_days": int(parsed_data.get("schedule_impact_days", 0)),
                "risk_level": self._validate_risk_level(parsed_data.get("risk_level", "Medium")),
                "affected_entities": list(parsed_data.get("affected_entities", [])),
                "recommendation": str(parsed_data.get("recommendation", "Review required")),
                "confidence_score": float(parsed_data.get("confidence_score", 0.7)),
            }

            logger.info(f"Successfully parsed requirements with confidence: {result['confidence_score']}")
            return result

        except Exception as e:
            logger.error(f"Error parsing requirements: {e}")
            raise ValueError(f"Failed to parse requirements: {e}") from e

    def _validate_risk_level(self, risk_level: str) -> str:
        """Validate and normalize risk level.

        Args:
            risk_level: Risk level string from LLM

        Returns:
            Normalized risk level (Low/Medium/High)
        """
        level = risk_level.strip().capitalize()
        if level not in ["Low", "Medium", "High"]:
            logger.warning(f"Invalid risk level '{risk_level}', defaulting to Medium")
            return "Medium"
        return level

    async def analyze_with_impact(
        self,
        project_id: UUID,
        title: str,
        description: str,
        reason: str,
        change_order_id: UUID | None = None,
        branch_name: str | None = None,
    ) -> dict[str, Any]:
        """Parse requirements and integrate with actual impact analysis.

        Combines AI-based requirement parsing with actual project data analysis
        to provide a comprehensive change order draft with accurate impact assessment.

        Args:
            project_id: UUID of the project
            title: Initial change order title
            description: Detailed description of the change
            reason: Business reason for the change
            change_order_id: Optional UUID of existing change order for impact analysis
            branch_name: Optional branch name for impact analysis

        Returns:
            Dictionary with parsed and analyzed change order data, including:
            - All fields from parse_requirements()
            - actual_impact: Results from ImpactAnalysisService if available
            - analysis_summary: Human-readable summary of the analysis

        Raises:
            ValueError: If parsing or impact analysis fails
        """
        # First, parse the requirements with AI
        parsed_data = await self.parse_requirements(
            project_id=project_id,
            title=title,
            description=description,
            reason=reason,
        )

        # Then, get actual impact analysis if we have a change order ID
        if change_order_id and branch_name:
            try:
                impact_analysis = await self._impact_service.analyze_impact(
                    change_order_id=change_order_id,
                    branch_name=branch_name,
                )
                # Merge AI estimates with actual data
                # Use actual data where available, fall back to AI estimates
                if impact_analysis.kpi_scorecard:
                    parsed_data["actual_budget_impact"] = Decimal(
                        str(impact_analysis.kpi_scorecard.budget_delta or 0)
                    )
                    parsed_data["actual_impact_available"] = True

            except Exception as e:
                logger.warning(f"Impact analysis failed, using AI estimates only: {e}")
                parsed_data["actual_impact_available"] = False

        # Generate analysis summary
        summary_parts = [
            f"Change Order: {parsed_data['title']}",
            f"Estimated Budget Impact: €{parsed_data['budget_impact']:,.2f}",
            f"Estimated Schedule Impact: {parsed_data['schedule_impact_days']} days",
            f"Risk Level: {parsed_data['risk_level']}",
            f"Recommendation: {parsed_data['recommendation']}",
        ]

        if parsed_data.get("actual_impact_available"):
            summary_parts.append("(Based on actual project analysis)")

        parsed_data["analysis_summary"] = "\n".join(summary_parts)

        return parsed_data
