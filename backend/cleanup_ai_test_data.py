#!/usr/bin/env python3
"""Clean up AI tools test data from the database."""

import asyncio
from sqlalchemy import text
from app.db.session import async_session_maker


async def cleanup_ai_test_data():
    """Delete all AI tools test data."""
    async with async_session_maker() as session:
        # Get all cost element codes that start with CE-
        result = await session.execute(
            text("SELECT DISTINCT cost_element_id FROM cost_elements WHERE code LIKE 'CE-%'")
        )
        ce_ids = [row[0] for row in result]

        if ce_ids:
            placeholders = ','.join(f':id{i}' for i in range(len(ce_ids)))
            params = {f'id{i}': ce_id for i, ce_id in enumerate(ce_ids)}

            # Delete progress entries
            await session.execute(
                text(f"DELETE FROM progress_entries WHERE cost_element_id IN ({placeholders})"),
                params
            )

            # Delete cost registrations
            await session.execute(
                text(f"DELETE FROM cost_registrations WHERE cost_element_id IN ({placeholders})"),
                params
            )

            # Get forecast IDs
            result = await session.execute(
                text("SELECT DISTINCT forecast_id FROM cost_elements WHERE code LIKE 'CE-%' AND forecast_id IS NOT NULL")
            )
            forecast_ids = [row[0] for row in result]

            # Delete cost elements (use the original placeholders)
            await session.execute(
                text(f"DELETE FROM cost_elements WHERE cost_element_id IN ({placeholders})"),
                params
            )

            # Get forecast IDs
            result = await session.execute(
                text("SELECT DISTINCT forecast_id FROM cost_elements WHERE code LIKE 'CE-%' AND forecast_id IS NOT NULL")
            )
            forecast_ids = [row[0] for row in result]

            if forecast_ids:
                placeholders_f = ','.join(f':fid{i}' for i in range(len(forecast_ids)))
                params_f = {f'fid{i}': fid for i, fid in enumerate(forecast_ids)}
                await session.execute(
                    text(f"DELETE FROM forecasts WHERE forecast_id IN ({placeholders_f})"),
                    params_f
                )

        # Delete WBEs
        await session.execute(text("DELETE FROM wbes WHERE code LIKE 'AI-TEST-%'"))

        # Delete project (do this AFTER WBEs since WBEs reference project)
        result = await session.execute(text("DELETE FROM projects WHERE code = 'AI-TEST-001'"))

        await session.commit()
        print(f"Cleaned up AI tools test data: {len(ce_ids) if ce_ids else 0} cost elements deleted")


if __name__ == "__main__":
    asyncio.run(cleanup_ai_test_data())
