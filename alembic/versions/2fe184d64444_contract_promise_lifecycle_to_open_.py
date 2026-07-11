"""contract_promise_lifecycle_to_open_closed

Revision ID: 2fe184d64444
Revises: a33848128f13
Create Date: 2026-07-11 09:09:33.666459

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2fe184d64444'
down_revision: Union[str, Sequence[str], None] = 'a33848128f13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Contract Promise lifecycle to OPEN/CLOSED; drop old 5-state enum."""
    # 1. Convert the native enum column to plain VARCHAR so we can change values
    op.execute(
        "ALTER TABLE expected_inflow_promises ALTER COLUMN status TYPE VARCHAR(32)"
    )
    # 2. Map old 5-state values to OPEN/CLOSED lifecycle
    op.execute(
        "UPDATE expected_inflow_promises SET status = CASE "
        "WHEN status IN ('EXPECTED', 'PARTIALLY_RECEIVED') THEN 'OPEN' "
        "ELSE 'CLOSED' END"
    )
    # 3. Drop the old native enum type
    op.execute("DROP TYPE IF EXISTS expectedinflowpromisestatus")


def downgrade() -> None:
    """Restore the old 5-state enum (best-effort; data cannot be unmapped)."""
    op.execute(
        "CREATE TYPE expectedinflowpromisestatus AS ENUM ("
        "'EXPECTED', 'PARTIALLY_RECEIVED', 'RESOLVED', 'CANCELLED', 'WRITTEN_OFF')"
    )
    op.execute(
        "ALTER TABLE expected_inflow_promises ALTER COLUMN status "
        "TYPE expectedinflowpromisestatus USING status::expectedinflowpromisestatus"
    )
