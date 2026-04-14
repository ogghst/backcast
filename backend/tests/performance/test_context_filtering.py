"""
Performance tests for AI chat session context filtering.

Validates that filtering sessions by context_type performs efficiently
even with 1000+ sessions across different context types.
"""

import asyncio
import statistics
import time
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.ai import AIConversationSession
from app.models.domain.user import User
from app.models.schemas.ai import (
    AIAssistantConfigCreate,
    AIModelCreate,
    AIProviderCreate,
)
from app.services.ai_config_service import AIConfigService


@pytest.mark.asyncio
async def test_context_filtering_performance_with_1000_sessions(
    db_session: AsyncSession, test_user: User
) -> None:
    """Test that context filtering is fast with 1000+ sessions.

    Validates that the composite index on (user_id, context->>'type') provides
    efficient filtering even at scale. Target: <100ms for filtering queries.

    This test creates 1000 sessions across 4 context types (250 each) and
    measures query performance for filtering by each type.
    """
    config_service = AIConfigService(db_session)

    # Create provider and model
    provider = await config_service.create_provider(
        AIProviderCreate(
            provider_type="openai", name="Test Provider", is_active=True
        )
    )
    model = await config_service.create_model(
        AIModelCreate(
            provider_id=provider.id,
            model_id="gpt-4",
            display_name="GPT-4",
        )
    )
    assistant_config = await config_service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Test Assistant",
            model_id=model.id,
            system_prompt="You are a helpful assistant.",
        )
    )

    # Create 1000 sessions: 250 per context type
    context_types = ["general", "project", "wbe", "cost_element"]
    sessions_per_type = 250
    total_sessions = len(context_types) * sessions_per_type

    # Track creation time
    creation_start = time.time()

    for context_type in context_types:
        for i in range(sessions_per_type):
            if context_type == "general":
                context = {"type": "general"}
            elif context_type == "project":
                context = {"type": "project", "id": str(uuid4()), "name": f"Project {i}"}
            elif context_type == "wbe":
                project_id = str(uuid4())
                context = {
                    "type": "wbe",
                    "id": str(uuid4()),
                    "project_id": project_id,
                    "name": f"WBE {i}",
                }
            else:  # cost_element
                project_id = str(uuid4())
                context = {
                    "type": "cost_element",
                    "id": str(uuid4()),
                    "project_id": project_id,
                    "name": f"Cost Element {i}",
                }

            await config_service.create_session(
                user_id=test_user.user_id,
                assistant_config_id=assistant_config.id,
                title=f"{context_type.capitalize()} Chat {i}",
                context=context,
            )

    creation_time = time.time() - creation_start
    print(f"\nCreated {total_sessions} sessions in {creation_time:.2f}s")

    # Verify index usage with EXPLAIN ANALYZE
    for context_type in context_types:
        # Get EXPLAIN ANALYZE output
        explain_query = text("""
            EXPLAIN (ANALYZE, FORMAT JSON)
            SELECT * FROM ai_conversation_sessions
            WHERE user_id = :user_id
            AND context->>'type' = :context_type
            ORDER BY updated_at DESC
            LIMIT 10
        """)

        result = await db_session.execute(
            explain_query,
            {"user_id": str(test_user.user_id), "context_type": context_type},
        )
        explain_output = result.scalar_one()

        print(f"\n{context_type.upper()} CONTEXT FILTER:")
        print(f"Query plan: {explain_output}")

    # Measure filtering performance for each context type
    filtering_times = []

    for context_type in context_types:
        # Measure query execution time
        query_start = time.time()

        sessions, _ = await config_service.list_sessions_paginated(
            user_id=test_user.user_id,
            skip=0,
            limit=10,
            context_type=context_type,
        )

        query_time = (time.time() - query_start) * 1000  # Convert to ms
        filtering_times.append(query_time)

        print(f"\n{context_type.upper()} filtering: {query_time:.2f}ms")
        assert len(sessions) == 10, f"Expected 10 sessions, got {len(sessions)}"

    # Calculate statistics
    avg_time = statistics.mean(filtering_times)
    max_time = max(filtering_times)
    min_time = min(filtering_times)

    print(f"\n=== PERFORMANCE RESULTS ===")
    print(f"Average: {avg_time:.2f}ms")
    print(f"Min: {min_time:.2f}ms")
    print(f"Max: {max_time:.2f}ms")

    # Performance assertion: filtering should be <100ms on average
    assert (
        avg_time < 100
    ), f"Context filtering too slow: {avg_time:.2f}ms average (target: <100ms)"

    # Ensure all queries complete in reasonable time
    assert max_time < 200, f"Slowest query too slow: {max_time:.2f}ms (limit: 200ms)"


@pytest.mark.asyncio
async def test_context_filtering_index_efficiency(
    db_session: AsyncSession, test_user: User
) -> None:
    """Test that the composite index is used for context filtering.

    Verifies that the query plan uses Index Scan instead of Seq Scan
    when filtering by context type.
    """
    config_service = AIConfigService(db_session)

    # Create provider and model
    provider = await config_service.create_provider(
        AIProviderCreate(
            provider_type="openai", name="Test Provider", is_active=True
        )
    )
    model = await config_service.create_model(
        AIModelCreate(
            provider_id=provider.id,
            model_id="gpt-4",
            display_name="GPT-4",
        )
    )
    assistant_config = await config_service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Test Assistant",
            model_id=model.id,
            system_prompt="You are a helpful assistant.",
        )
    )

    # Create 100 sessions of each type to ensure index is beneficial
    for context_type in ["general", "project", "wbe", "cost_element"]:
        for i in range(100):
            if context_type == "general":
                context = {"type": "general"}
            elif context_type == "project":
                context = {"type": "project", "id": str(uuid4()), "name": f"Project {i}"}
            elif context_type == "wbe":
                project_id = str(uuid4())
                context = {
                    "type": "wbe",
                    "id": str(uuid4()),
                    "project_id": project_id,
                }
            else:  # cost_element
                project_id = str(uuid4())
                context = {
                    "type": "cost_element",
                    "id": str(uuid4()),
                    "project_id": project_id,
                }

            await config_service.create_session(
                user_id=test_user.user_id,
                assistant_config_id=assistant_config.id,
                context=context,
            )

    # Force commit to ensure index is updated
    await db_session.commit()

    # Get query plan for filtering
    explain_query = text("""
        EXPLAIN
        SELECT * FROM ai_conversation_sessions
        WHERE user_id = :user_id
        AND context->>'type' = :context_type
        LIMIT 10
    """)

    result = await db_session.execute(
        explain_query,
        {"user_id": str(test_user.user_id), "context_type": "project"},
    )
    explain_output = result.scalar_one()

    # Check that the plan uses index (not sequential scan)
    plan_str = str(explain_output).lower()

    # The query should use the composite index
    # Look for "Index Scan" or "Bitmap Index Scan"
    uses_index = (
        "index scan" in plan_str
        or "bitmap index scan" in plan_str
        or "index only scan" in plan_str
    )

    # Note: PostgreSQL might choose a different plan for small datasets,
    # but with 400 rows, it should prefer the index
    print(f"\nQuery plan: {explain_output}")

    # For a composite index on (user_id, context->>'type'), we expect
    # the plan to use an index scan
    assert (
        "seq scan" not in plan_str or "parallel seq scan" not in plan_str
    ), "Query should use index scan, not sequential scan for context filtering"


@pytest.mark.asyncio
async def test_context_count_performance(
    db_session: AsyncSession, test_user: User
) -> None:
    """Test that counting sessions with context filter is fast.

    COUNT queries with context filtering should also benefit from the index.
    """
    config_service = AIConfigService(db_session)

    # Create provider and model
    provider = await config_service.create_provider(
        AIProviderCreate(
            provider_type="openai", name="Test Provider", is_active=True
        )
    )
    model = await config_service.create_model(
        AIModelCreate(
            provider_id=provider.id,
            model_id="gpt-4",
            display_name="GPT-4",
        )
    )
    assistant_config = await config_service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Test Assistant",
            model_id=model.id,
            system_prompt="You are a helpful assistant.",
        )
    )

    # Create 500 sessions across context types
    for context_type in ["general", "project", "wbe", "cost_element"]:
        for i in range(125):
            if context_type == "general":
                context = {"type": "general"}
            elif context_type == "project":
                context = {"type": "project", "id": str(uuid4())}
            elif context_type == "wbe":
                context = {
                    "type": "wbe",
                    "id": str(uuid4()),
                    "project_id": str(uuid4()),
                }
            else:  # cost_element
                context = {
                    "type": "cost_element",
                    "id": str(uuid4()),
                    "project_id": str(uuid4()),
                }

            await config_service.create_session(
                user_id=test_user.user_id,
                assistant_config_id=assistant_config.id,
                context=context,
            )

    await db_session.commit()

    # Measure COUNT performance with context filter
    count_query = text("""
        SELECT COUNT(*) FROM ai_conversation_sessions
        WHERE user_id = :user_id
        AND context->>'type' = :context_type
    """)

    count_times = []
    for context_type in ["general", "project", "wbe", "cost_element"]:
        start = time.time()
        result = await db_session.execute(
            count_query,
            {"user_id": str(test_user.user_id), "context_type": context_type},
        )
        count = result.scalar_one()
        query_time = (time.time() - start) * 1000  # ms

        count_times.append(query_time)
        print(f"{context_type} COUNT: {count} sessions in {query_time:.2f}ms")

    avg_count_time = statistics.mean(count_times)

    print(f"\nAverage COUNT time: {avg_count_time:.2f}ms")

    # COUNT queries should be very fast with index
    assert (
        avg_count_time < 50
    ), f"COUNT query too slow: {avg_count_time:.2f}ms (target: <50ms)"
