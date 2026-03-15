import asyncio
from uuid import UUID

from app.db.session import async_session_maker
from app.services.ai_config_service import AIConfigService


async def main():
    async with async_session_maker() as session:
        ai_service = AIConfigService(session=session)
        configs = await ai_service.list_provider_configs(UUID("01234567-89ab-cdef-0123-456789abcde0"), decrypt=True)
        for cfg in configs:
            if cfg.key == "api_key":
                print(f"Decrypted API key: '{cfg.value}'")

if __name__ == "__main__":
    import sys
    sys.path.append("/home/nicola/dev/backcast_evs/backend/app")
    asyncio.run(main())
