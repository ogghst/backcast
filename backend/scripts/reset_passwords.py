#!/usr/bin/env python3
"""One-time script to reset user passwords with proper hashing.

Context: Bug #6 — non-admin users couldn't log in because their passwords
were either not properly hashed or unknown. This script resets all seed
user passwords using the application's bcrypt hashing.
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import update

# Add the backend directory to sys.path to allow importing app
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from app.core.security import get_password_hash  # noqa: E402
from app.db.session import async_session_maker  # noqa: E402
from app.models.domain.user import User  # noqa: E402

PASSWORDS = {
    "admin@backcast.org": "adminadmin",
    "pm@backcast.org": "backcast",
    "viewer@backcast.org": "backcast",
    "dept.head@backcast.org": "backcast",
    "director@backcast.org": "backcast",
    "eng.lead@backcast.org": "backcast",
    "const.super@backcast.org": "backcast",
}


async def reset_passwords() -> None:
    """Reset all seed user passwords with proper bcrypt hashing."""
    async with async_session_maker() as session:
        for email, password in PASSWORDS.items():
            hashed = get_password_hash(password)
            stmt = (
                update(User).where(User.email == email).values(hashed_password=hashed)
            )
            await session.execute(stmt)
            print(f"Reset password for {email}")
        await session.commit()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(reset_passwords())
