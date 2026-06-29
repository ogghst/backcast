"""CurrencyRate domain model - non-versioned reference ledger.

Stores FX rates to the project base currency (default EUR) as of an
``effective_date``. Used to convert foreign-currency amounts to base for
portfolio rollups. Non-versioned reference data — satisfies
SimpleEntityProtocol via SimpleEntityBase.
"""

from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase


class CurrencyRate(SimpleEntityBase):
    """CurrencyRate entity - non-versioned FX reference ledger.

    Attributes:
        currency: ISO-4217 currency code (e.g. "EUR", "USD").
        rate_to_base: Conversion factor to the base currency (1 unit of
            ``currency`` = ``rate_to_base`` units of base). EUR->EUR is 1.0.
        effective_date: Date from which the rate is valid (inclusive).
    """

    __tablename__ = "currency_rates"

    currency: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    rate_to_base: Mapped[Decimal] = mapped_column(Numeric(15, 6), nullable=False)
    effective_date: Mapped[date] = mapped_column(sa.Date, nullable=False, index=True)

    def __repr__(self) -> str:
        return (
            f"<CurrencyRate(id={self.id}, currency={self.currency!r}, "
            f"rate_to_base={self.rate_to_base}, effective_date={self.effective_date})>"
        )
