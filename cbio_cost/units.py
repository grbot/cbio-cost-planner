"""Unit conversion constants, isolated so they can be changed in one place.

This project uses the decimal convention ``1 TB = 1024 GB`` to remain
consistent with the existing CBIO proposal. This is a *decimal-TB-of-binary-GB*
hybrid, not IEC binary units (which would be TiB = 1024 GiB) and not pure
SI decimal units (which would be TB = 1000 GB). It is kept isolated here so
the convention can be revisited later without touching calculation logic.
"""

from decimal import Decimal

GB_PER_TB = Decimal(1024)


def gb_to_tb(value_gb: Decimal) -> Decimal:
    """Convert a quantity in GB to TB using the project's GB_PER_TB constant."""
    return value_gb / GB_PER_TB


def tb_to_gb(value_tb: Decimal) -> Decimal:
    """Convert a quantity in TB to GB using the project's GB_PER_TB constant."""
    return value_tb * GB_PER_TB
