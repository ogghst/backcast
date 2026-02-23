import asyncio

import httpx


async def main():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:51520") as client:
        # We might need to bypass auth or use the test auth token if there's one
        # Try getting it directly
        try:
            r = await client.get(
                "/api/v1/evm/wbe/3a42f62c-96f8-5392-bff1-2e16f97734f0/timeseries?granularity=week&branch=main&branch_mode=merge"
            )
            print("Status:", r.status_code)

            data = r.json()
            for p in data.get("points", [])[:5]:
                print(
                    f"Date: {p['date']}, EV: {p['ev']}, AC: {p['ac']}, PV: {p['pv']}, CPI: {p.get('cpi')}, SPI: {p.get('spi')}"
                )
        except Exception as e:
            print("Error:", e)


asyncio.run(main())
