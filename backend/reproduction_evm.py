import asyncio
import sys
import os
from datetime import datetime
from decimal import Decimal
from uuid import UUID

# Ensure backend directory is in python path
sys.path.append(os.getcwd())

from app.db.session import async_session_maker
from app.services.evm_service import EVMService

async def main():
    async with async_session_maker() as db:
        service = EVMService(db)
        ce_id = UUID("71a09036-5008-5f09-a444-eeecc5e79a41")
        # Time specified in user request (must be UTC for tstzrange comparison)
        from datetime import timezone
        control_date = datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc)
        
        print(f"--- Reproduction for {ce_id} at {control_date} ---")
        try:
            metrics = await service.calculate_evm_metrics(
                cost_element_id=ce_id,
                control_date=control_date
            )
            print(f"BAC: {metrics.bac}")
            print(f"EAC: {metrics.eac}")
            print(f"AC: {metrics.ac}")
            print(f"EV: {metrics.ev}")
            print(f"PV: {metrics.pv}")
            print(f"CPI: {metrics.cpi}")
            print(f"SPI: {metrics.spi}")
            print(f"VAC: {metrics.vac}")
            print(f"ETC: {metrics.etc}")
            print(f"CPI (Forecast): {metrics.cpi_forecast}")
            print(f"PV (Forecast): {metrics.pv_forecast}")
            print(f"Warning: {metrics.warning}")
            
            # Check correctness according to standard formulas
            print("\n--- Verification ---")
            if metrics.ac and metrics.ev is not None:
                calc_cpi = metrics.ev / metrics.ac if metrics.ac != 0 else None
                print(f"Calculated CPI (EV/AC): {calc_cpi}")
                
            if metrics.bac and metrics.eac:
                 implied_cpi = metrics.bac / metrics.eac
                 print(f"Implied CPI (BAC/EAC): {implied_cpi}")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
