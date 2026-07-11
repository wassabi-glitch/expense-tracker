"""remove_debt_status_and_product_kind

Revision ID: 4ce26c366899
Revises: 2348bf134499
Create Date: 2026-07-10 13:26:14.013623

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4ce26c366899'
down_revision: Union[str, Sequence[str], None] = '2348bf134499'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove legacy ``debts.status`` and ``debts.product_kind`` columns.

    ADRs 0026-0027 — lifecycle is now derived from balance / due-date / archive,
    and standalone Debt no longer uses Payment Plan product taxonomy.
    """
    op.drop_index(op.f('ix_debts_owner_product'), table_name='debts')
    op.drop_index(op.f('ix_debts_owner_status'), table_name='debts')
    op.drop_column('debts', 'product_kind')
    op.drop_column('debts', 'status')


def downgrade() -> None:
    """Restore removed columns (development-only — no data preservation)."""
    op.add_column('debts', sa.Column('status', postgresql.ENUM(
        'ACTIVE', 'PAID', 'FORGIVEN', 'ARCHIVED', 'OVERDUE',
        'DEFAULTED', 'IN_COLLECTION', 'SETTLED', 'WRITTEN_OFF',
        name='debtstatus'), server_default=sa.text("'ACTIVE'::debtstatus"),
        autoincrement=False, nullable=False))
    op.add_column('debts', sa.Column('product_kind', postgresql.ENUM(
        'INFORMAL_DEBT', 'BANK_LOAN', 'CAR_LOAN', 'MORTGAGE',
        'STORE_INSTALLMENT', 'SERVICE_PAY_LATER',
        'PERSONAL_REIMBURSEMENT', 'CLIENT_RECEIVABLE', 'OTHER',
        name='debtproductkind'), autoincrement=False, nullable=True))
    op.create_index(op.f('ix_debts_owner_status'), 'debts', ['owner_id', 'status'], unique=False)
    op.create_index(op.f('ix_debts_owner_product'), 'debts', ['owner_id', 'product_kind'], unique=False)

    # Remove project-related changes that were captured by the original
    # autogenerate but belong to a different migration.
    op.drop_constraint('uq_overlay_proj_subcat_res_project_subcat_month', 'overlay_project_subcategory_reservations', type_='unique')
    op.create_unique_constraint(op.f('uq_overlay_project_subcategory_reservations_project_subcategory'), 'overlay_project_subcategory_reservations', ['project_id', 'user_subcategory_id', 'budget_year', 'budget_month'], postgresql_nulls_not_distinct=False)
    op.add_column('expense_session_draft_items', sa.Column('isolated_project_subcategory_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key(op.f('fk_expense_session_draft_items_isolated_project_subcategory_id'), 'expense_session_draft_items', 'isolated_project_subcategory_allocations', ['isolated_project_subcategory_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_expense_session_draft_items_isolated_project_subcategory_id'), 'expense_session_draft_items', ['isolated_project_subcategory_id'], unique=False)
    op.add_column('entity_ledger', sa.Column('isolated_project_subcategory_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key(op.f('fk_entity_ledger_isolated_project_subcategory_id'), 'entity_ledger', 'isolated_project_subcategory_allocations', ['isolated_project_subcategory_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_entity_ledger_isolated_project_subcategory_id'), 'entity_ledger', ['isolated_project_subcategory_id'], unique=False)
