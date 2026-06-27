"""Add independent payment plan accounting with strict wallet allocations

Revision ID: 29e810b4fc08
Revises: a32b1c2d3e4f
Create Date: 2026-06-27 06:56:01.267071

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29e810b4fc08'
down_revision: Union[str, Sequence[str], None] = 'a32b1c2d3e4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _backfill_legacy_payment_plan_accounting() -> None:
    op.execute(
        sa.text(
            """
            CREATE TEMPORARY TABLE _legacy_payment_plan_backing_debts
            ON COMMIT DROP
            AS
            SELECT
                p.id AS plan_id,
                p.owner_id,
                p.debt_id
            FROM payment_plans p
            WHERE p.debt_id IS NOT NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            WITH linked_plans AS (
                SELECT
                    p.id AS plan_id,
                    p.owner_id,
                    p.debt_id,
                    p.total_price,
                    p.down_payment,
                    p.remaining_amount,
                    p.start_date
                FROM payment_plans p
                JOIN _legacy_payment_plan_backing_debts lp
                  ON lp.plan_id = p.id
            ),
            opening_entries AS (
                SELECT
                    p.plan_id,
                    p.owner_id,
                    p.total_price,
                    p.down_payment,
                    p.remaining_amount,
                    p.start_date,
                    e.financial_event_id,
                    e.amount_delta AS source_amount_delta,
                    e.principal_delta AS source_principal_delta,
                    e.charge_delta AS source_charge_delta,
                    e.balance_after AS source_balance_after,
                    e.event_subtype,
                    e.entry_date,
                    e.note,
                    e.created_at
                FROM linked_plans p
                LEFT JOIN LATERAL (
                    SELECT *
                    FROM debt_ledger_entries e
                    WHERE e.owner_id = p.owner_id
                      AND e.debt_id = p.debt_id
                      AND e.entry_type = 'INITIAL'
                      AND e.status = 'POSTED'
                    ORDER BY e.entry_date ASC, e.id ASC
                    LIMIT 1
                ) e ON true
            ),
            normalized_openings AS (
                SELECT
                    plan_id,
                    owner_id,
                    financial_event_id,
                    CASE
                        WHEN source_amount_delta IS NOT NULL THEN source_amount_delta
                        ELSE total_price - down_payment
                    END AS amount_delta,
                    CASE
                        WHEN source_principal_delta IS NOT NULL THEN source_principal_delta
                        ELSE total_price - down_payment
                    END AS principal_delta,
                    COALESCE(source_charge_delta, 0) AS charge_delta,
                    CASE
                        WHEN source_balance_after IS NOT NULL THEN source_balance_after
                        WHEN source_amount_delta IS NOT NULL THEN source_amount_delta
                        ELSE total_price - down_payment
                    END AS balance_after,
                    COALESCE(event_subtype, 'PAYMENT_PLAN_ORIGIN') AS event_subtype,
                    COALESCE(entry_date, start_date) AS entry_date,
                    COALESCE(note, 'Migrated payment-plan opening balance') AS note,
                    COALESCE(created_at, now()) AS created_at
                FROM opening_entries
            )
            INSERT INTO payment_plan_ledger_entries (
                owner_id,
                plan_id,
                financial_event_id,
                entry_type,
                amount_delta,
                principal_delta,
                charge_delta,
                balance_after,
                event_subtype,
                source,
                is_reversible,
                status,
                entry_date,
                note,
                created_at
            )
            SELECT
                owner_id,
                plan_id,
                financial_event_id,
                'INITIAL',
                amount_delta,
                principal_delta,
                charge_delta,
                balance_after,
                event_subtype,
                'SYSTEM',
                false,
                'POSTED',
                entry_date,
                note,
                created_at
            FROM normalized_openings
            WHERE amount_delta > 0
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TEMPORARY TABLE _legacy_payment_plan_transaction_map (
                old_debt_transaction_id integer PRIMARY KEY,
                new_payment_plan_transaction_id integer NOT NULL,
                plan_id integer NOT NULL
            ) ON COMMIT DROP
            """
        )
    )

    op.execute(
        sa.text(
            """
            DO $$
            DECLARE source_row record;
            DECLARE inserted_id integer;
            BEGIN
                FOR source_row IN
                    WITH source_transactions AS (
                        SELECT DISTINCT
                            dt.id AS old_debt_transaction_id,
                            lp.plan_id,
                            dt.owner_id,
                            dt.amount,
                            dt.date,
                            dt.note,
                            dt.created_at
                        FROM payment_plan_payment_allocations ppa
                        JOIN payment_plan_payments pp
                          ON pp.id = ppa.payment_plan_payment_id
                        JOIN _legacy_payment_plan_backing_debts lp
                          ON lp.plan_id = pp.plan_id
                        JOIN debt_transactions dt
                          ON dt.id = ppa.debt_transaction_id
                        WHERE ppa.debt_transaction_id IS NOT NULL

                        UNION

                        SELECT DISTINCT
                            dt.id AS old_debt_transaction_id,
                            lp.plan_id,
                            dt.owner_id,
                            dt.amount,
                            dt.date,
                            dt.note,
                            dt.created_at
                        FROM payment_plan_payments pp
                        JOIN _legacy_payment_plan_backing_debts lp
                          ON lp.plan_id = pp.plan_id
                        JOIN debt_ledger_entries dle
                          ON dle.id = pp.debt_ledger_entry_id
                        JOIN debt_transactions dt
                          ON dt.id = dle.source_debt_transaction_id
                        WHERE pp.debt_ledger_entry_id IS NOT NULL
                    )
                    SELECT *
                    FROM source_transactions
                    ORDER BY old_debt_transaction_id
                LOOP
                    INSERT INTO payment_plan_transactions (
                        owner_id,
                        plan_id,
                        amount,
                        date,
                        note,
                        created_at
                    )
                    VALUES (
                        source_row.owner_id,
                        source_row.plan_id,
                        source_row.amount,
                        source_row.date,
                        source_row.note,
                        source_row.created_at
                    )
                    RETURNING id INTO inserted_id;

                    INSERT INTO _legacy_payment_plan_transaction_map (
                        old_debt_transaction_id,
                        new_payment_plan_transaction_id,
                        plan_id
                    )
                    VALUES (
                        source_row.old_debt_transaction_id,
                        inserted_id,
                        source_row.plan_id
                    );
                END LOOP;
            END $$;
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO payment_plan_transaction_wallet_allocations (
                owner_id,
                plan_id,
                payment_plan_transaction_id,
                wallet_id,
                amount,
                created_at
            )
            SELECT
                dtwa.owner_id,
                tx_map.plan_id,
                tx_map.new_payment_plan_transaction_id,
                dtwa.wallet_id,
                SUM(dtwa.amount),
                MIN(dtwa.created_at)
            FROM debt_transaction_wallet_allocations dtwa
            JOIN _legacy_payment_plan_transaction_map tx_map
              ON tx_map.old_debt_transaction_id = dtwa.debt_transaction_id
            GROUP BY
                dtwa.owner_id,
                tx_map.plan_id,
                tx_map.new_payment_plan_transaction_id,
                dtwa.wallet_id
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO payment_plan_transaction_wallet_allocations (
                owner_id,
                plan_id,
                payment_plan_transaction_id,
                wallet_id,
                amount,
                created_at
            )
            SELECT
                ppa.owner_id,
                pp.plan_id,
                tx_map.new_payment_plan_transaction_id,
                ppa.wallet_id,
                SUM(ppa.amount),
                MIN(ppa.created_at)
            FROM payment_plan_payment_allocations ppa
            JOIN payment_plan_payments pp
              ON pp.id = ppa.payment_plan_payment_id
            JOIN _legacy_payment_plan_transaction_map tx_map
              ON tx_map.old_debt_transaction_id = ppa.debt_transaction_id
            WHERE ppa.wallet_id IS NOT NULL
            GROUP BY
                ppa.owner_id,
                pp.plan_id,
                tx_map.new_payment_plan_transaction_id,
                ppa.wallet_id
            ON CONFLICT ON CONSTRAINT uq_payment_plan_txn_wallet_allocations_wallet
            DO NOTHING
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TEMPORARY TABLE _legacy_payment_plan_charge_map (
                old_debt_charge_id integer PRIMARY KEY,
                new_payment_plan_charge_id integer NOT NULL,
                plan_id integer NOT NULL
            ) ON COMMIT DROP
            """
        )
    )

    op.execute(
        sa.text(
            """
            DO $$
            DECLARE source_row record;
            DECLARE inserted_id integer;
            BEGIN
                FOR source_row IN
                    SELECT
                        c.id AS old_debt_charge_id,
                        lp.plan_id,
                        c.owner_id,
                        c.amount,
                        c.reason,
                        c.date,
                        c.created_at
                    FROM debt_charges c
                    JOIN _legacy_payment_plan_backing_debts lp
                      ON lp.debt_id = c.debt_id
                     AND lp.owner_id = c.owner_id
                    ORDER BY c.date ASC, c.id ASC
                LOOP
                    INSERT INTO payment_plan_charges (
                        owner_id,
                        plan_id,
                        amount,
                        reason,
                        date,
                        created_at
                    )
                    VALUES (
                        source_row.owner_id,
                        source_row.plan_id,
                        source_row.amount,
                        source_row.reason,
                        source_row.date,
                        source_row.created_at
                    )
                    RETURNING id INTO inserted_id;

                    INSERT INTO _legacy_payment_plan_charge_map (
                        old_debt_charge_id,
                        new_payment_plan_charge_id,
                        plan_id
                    )
                    VALUES (
                        source_row.old_debt_charge_id,
                        inserted_id,
                        source_row.plan_id
                    );
                END LOOP;
            END $$;
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TEMPORARY TABLE _legacy_payment_plan_ledger_map (
                old_debt_ledger_entry_id integer PRIMARY KEY,
                new_payment_plan_ledger_entry_id integer NOT NULL,
                plan_id integer NOT NULL
            ) ON COMMIT DROP
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TEMPORARY TABLE _legacy_payment_plan_writeoff_transaction_map (
                old_debt_ledger_entry_id integer PRIMARY KEY,
                new_payment_plan_transaction_id integer NOT NULL,
                plan_id integer NOT NULL
            ) ON COMMIT DROP
            """
        )
    )

    op.execute(
        sa.text(
            """
            DO $$
            DECLARE source_row record;
            DECLARE inserted_id integer;
            BEGIN
                FOR source_row IN
                    SELECT
                        dle.id AS old_debt_ledger_entry_id,
                        lp.plan_id,
                        dle.owner_id,
                        ABS(dle.amount_delta) AS amount,
                        dle.entry_date AS date,
                        COALESCE(dle.note, 'Payment plan write-off') AS note,
                        dle.created_at
                    FROM debt_ledger_entries dle
                    JOIN _legacy_payment_plan_backing_debts lp
                      ON lp.debt_id = dle.debt_id
                     AND lp.owner_id = dle.owner_id
                    WHERE dle.entry_type IN ('ADJUSTMENT', 'FORGIVENESS')
                      AND dle.amount_delta < 0
                      AND (
                          dle.event_subtype = 'PAYMENT_PLAN_WRITE_OFF'
                          OR COALESCE(dle.note, '') ILIKE 'Write-off for%payment%'
                      )
                    ORDER BY dle.entry_date ASC, dle.id ASC
                LOOP
                    INSERT INTO payment_plan_transactions (
                        owner_id,
                        plan_id,
                        amount,
                        date,
                        note,
                        created_at
                    )
                    VALUES (
                        source_row.owner_id,
                        source_row.plan_id,
                        source_row.amount,
                        source_row.date,
                        source_row.note,
                        source_row.created_at
                    )
                    RETURNING id INTO inserted_id;

                    INSERT INTO _legacy_payment_plan_writeoff_transaction_map (
                        old_debt_ledger_entry_id,
                        new_payment_plan_transaction_id,
                        plan_id
                    )
                    VALUES (
                        source_row.old_debt_ledger_entry_id,
                        inserted_id,
                        source_row.plan_id
                    );
                END LOOP;
            END $$;
            """
        )
    )

    op.execute(
        sa.text(
            """
            DO $$
            DECLARE source_row record;
            DECLARE inserted_id integer;
            BEGIN
                FOR source_row IN
                    SELECT
                        dle.id AS old_debt_ledger_entry_id,
                        lp.plan_id,
                        dle.owner_id,
                        dle.financial_event_id,
                        COALESCE(
                            tx_map.new_payment_plan_transaction_id,
                            writeoff_tx_map.new_payment_plan_transaction_id
                        ) AS new_payment_plan_transaction_id,
                        charge_map.new_payment_plan_charge_id,
                        CASE
                            WHEN dle.entry_type IN ('ADJUSTMENT', 'FORGIVENESS')
                                THEN 'ADJUSTMENT'
                            ELSE dle.entry_type::text
                        END AS entry_type,
                        dle.amount_delta,
                        dle.principal_delta,
                        dle.charge_delta,
                        dle.balance_after,
                        dle.event_subtype,
                        dle.is_reversible,
                        dle.status,
                        dle.entry_date,
                        dle.note,
                        dle.created_at
                    FROM debt_ledger_entries dle
                    JOIN _legacy_payment_plan_backing_debts lp
                      ON lp.debt_id = dle.debt_id
                     AND lp.owner_id = dle.owner_id
                    LEFT JOIN _legacy_payment_plan_transaction_map tx_map
                      ON tx_map.old_debt_transaction_id = dle.source_debt_transaction_id
                    LEFT JOIN _legacy_payment_plan_charge_map charge_map
                      ON charge_map.old_debt_charge_id = dle.source_debt_charge_id
                    LEFT JOIN _legacy_payment_plan_writeoff_transaction_map writeoff_tx_map
                      ON writeoff_tx_map.old_debt_ledger_entry_id = dle.id
                    WHERE dle.entry_type IN ('PAYMENT', 'CHARGE')
                       OR (
                           dle.entry_type IN ('ADJUSTMENT', 'FORGIVENESS')
                           AND dle.amount_delta < 0
                           AND (
                               dle.event_subtype = 'PAYMENT_PLAN_WRITE_OFF'
                               OR COALESCE(dle.note, '') ILIKE 'Write-off for%payment%'
                           )
                       )
                    ORDER BY dle.entry_date ASC, dle.id ASC
                LOOP
                    INSERT INTO payment_plan_ledger_entries (
                        owner_id,
                        plan_id,
                        financial_event_id,
                        source_transaction_id,
                        source_charge_id,
                        entry_type,
                        amount_delta,
                        principal_delta,
                        charge_delta,
                        balance_after,
                        event_subtype,
                        source,
                        is_reversible,
                        status,
                        entry_date,
                        note,
                        created_at
                    )
                    VALUES (
                        source_row.owner_id,
                        source_row.plan_id,
                        source_row.financial_event_id,
                        source_row.new_payment_plan_transaction_id,
                        source_row.new_payment_plan_charge_id,
                        source_row.entry_type::paymentplanledgerentrytype,
                        source_row.amount_delta,
                        source_row.principal_delta,
                        source_row.charge_delta,
                        source_row.balance_after,
                        source_row.event_subtype,
                        'SYSTEM',
                        source_row.is_reversible,
                        source_row.status,
                        source_row.entry_date,
                        source_row.note,
                        source_row.created_at
                    )
                    RETURNING id INTO inserted_id;

                    INSERT INTO _legacy_payment_plan_ledger_map (
                        old_debt_ledger_entry_id,
                        new_payment_plan_ledger_entry_id,
                        plan_id
                    )
                    VALUES (
                        source_row.old_debt_ledger_entry_id,
                        inserted_id,
                        source_row.plan_id
                    );
                END LOOP;
            END $$;
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE payment_plan_payment_allocations ppa
            SET
                payment_plan_transaction_id = migrated.new_payment_plan_transaction_id,
                payment_plan_ledger_entry_id = migrated.new_payment_plan_ledger_entry_id
            FROM (
                SELECT
                    ppa_inner.id AS allocation_id,
                    tx_map.new_payment_plan_transaction_id,
                    ledger_map.new_payment_plan_ledger_entry_id
                FROM payment_plan_payment_allocations ppa_inner
                JOIN payment_plan_payments pp
                  ON pp.id = ppa_inner.payment_plan_payment_id
                LEFT JOIN _legacy_payment_plan_transaction_map tx_map
                  ON tx_map.old_debt_transaction_id = ppa_inner.debt_transaction_id
                LEFT JOIN _legacy_payment_plan_ledger_map ledger_map
                  ON ledger_map.old_debt_ledger_entry_id = ppa_inner.debt_ledger_entry_id
                WHERE pp.plan_id IN (
                    SELECT plan_id FROM _legacy_payment_plan_backing_debts
                )
            ) migrated
            WHERE ppa.id = migrated.allocation_id
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE payment_plan_payments pp
            SET payment_plan_ledger_entry_id = ledger_map.new_payment_plan_ledger_entry_id
            FROM _legacy_payment_plan_ledger_map ledger_map
            WHERE pp.debt_ledger_entry_id = ledger_map.old_debt_ledger_entry_id
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE payment_plan_payments pp
            SET payment_plan_charge_id = charge_map.new_payment_plan_charge_id
            FROM _legacy_payment_plan_charge_map charge_map
            WHERE pp.debt_charge_id = charge_map.old_debt_charge_id
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE entity_ledger el
            SET
                debt_id = NULL,
                payment_plan_id = pp.plan_id,
                payment_plan_payment_id = pp.id
            FROM payment_plan_payment_allocations ppa
            JOIN payment_plan_payments pp
              ON pp.id = ppa.payment_plan_payment_id
            JOIN _legacy_payment_plan_backing_debts lp
              ON lp.plan_id = pp.plan_id
            WHERE el.event_id = ppa.financial_event_id
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE entity_ledger el
            SET
                debt_id = NULL,
                payment_plan_id = lp.plan_id
            FROM _legacy_payment_plan_backing_debts lp
            JOIN debts d
              ON d.id = lp.debt_id
             AND d.owner_id = lp.owner_id
            WHERE el.debt_id = lp.debt_id
              AND d.linked_event_id IS NOT NULL
              AND el.event_id = d.linked_event_id
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE goals g
            SET
                linked_payment_plan_id = lp.plan_id,
                linked_debt_id = NULL
            FROM _legacy_payment_plan_backing_debts lp
            WHERE g.owner_id = lp.owner_id
              AND g.linked_debt_id = lp.debt_id
              AND (
                  g.linked_payment_plan_id IS NULL
                  OR g.linked_payment_plan_id = lp.plan_id
              )
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE debts d
            SET
                archived_at = COALESCE(d.archived_at, now()),
                status = 'ARCHIVED'
            WHERE EXISTS (
                SELECT 1
                FROM _legacy_payment_plan_backing_debts lp
                WHERE lp.debt_id = d.id
                  AND lp.owner_id = d.owner_id
            )
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE payment_plans p
            SET debt_id = NULL
            FROM _legacy_payment_plan_backing_debts lp
            WHERE lp.plan_id = p.id
            """
        )
    )


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('payment_plan_charges',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('plan_id', sa.Integer(), nullable=False),
    sa.Column('amount', sa.BigInteger(), nullable=False),
    sa.Column('reason', sa.String(length=200), nullable=True),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('amount > 0', name='ck_payment_plan_charges_amount_positive'),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['plan_id'], ['payment_plans.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_plan_charges_id'), 'payment_plan_charges', ['id'], unique=False)
    op.create_index(op.f('ix_payment_plan_charges_owner_id'), 'payment_plan_charges', ['owner_id'], unique=False)
    op.create_index('ix_payment_plan_charges_plan_id', 'payment_plan_charges', ['plan_id'], unique=False)
    op.create_table('payment_plan_transactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('plan_id', sa.Integer(), nullable=False),
    sa.Column('amount', sa.BigInteger(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('note', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('amount > 0', name='ck_payment_plan_transactions_amount_positive'),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['plan_id'], ['payment_plans.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_plan_transactions_id'), 'payment_plan_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_payment_plan_transactions_owner_id'), 'payment_plan_transactions', ['owner_id'], unique=False)
    op.create_index(op.f('ix_payment_plan_transactions_plan_id'), 'payment_plan_transactions', ['plan_id'], unique=False)
    op.create_table('payment_plan_ledger_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('plan_id', sa.Integer(), nullable=False),
    sa.Column('financial_event_id', sa.Integer(), nullable=True),
    sa.Column('source_transaction_id', sa.Integer(), nullable=True),
    sa.Column('source_charge_id', sa.Integer(), nullable=True),
    sa.Column('reverses_entry_id', sa.Integer(), nullable=True),
    sa.Column('entry_type', sa.Enum('INITIAL', 'PAYMENT', 'CHARGE', 'ADJUSTMENT', 'REVERSAL', name='paymentplanledgerentrytype'), nullable=False),
    sa.Column('amount_delta', sa.BigInteger(), nullable=False),
    sa.Column('principal_delta', sa.BigInteger(), server_default='0', nullable=False),
    sa.Column('charge_delta', sa.BigInteger(), server_default='0', nullable=False),
    sa.Column('balance_after', sa.BigInteger(), nullable=True),
    sa.Column('event_subtype', sa.String(length=50), nullable=True),
    sa.Column('source', sa.Enum('USER', 'SYSTEM', name='paymentplanledgerentrysource'), server_default='USER', nullable=False),
    sa.Column('is_reversible', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('status', sa.String(length=20), server_default='POSTED', nullable=False),
    sa.Column('entry_date', sa.Date(), nullable=False),
    sa.Column('note', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('amount_delta != 0', name='ck_payment_plan_ledger_amount_delta_non_zero'),
    sa.ForeignKeyConstraint(['financial_event_id'], ['financial_events.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['plan_id'], ['payment_plans.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reverses_entry_id'], ['payment_plan_ledger_entries.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['source_charge_id'], ['payment_plan_charges.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['source_transaction_id'], ['payment_plan_transactions.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_plan_ledger_entries_financial_event_id'), 'payment_plan_ledger_entries', ['financial_event_id'], unique=False)
    op.create_index(op.f('ix_payment_plan_ledger_entries_id'), 'payment_plan_ledger_entries', ['id'], unique=False)
    op.create_index(op.f('ix_payment_plan_ledger_entries_owner_id'), 'payment_plan_ledger_entries', ['owner_id'], unique=False)
    op.create_index(op.f('ix_payment_plan_ledger_entries_plan_id'), 'payment_plan_ledger_entries', ['plan_id'], unique=False)
    op.create_index(op.f('ix_payment_plan_ledger_entries_reverses_entry_id'), 'payment_plan_ledger_entries', ['reverses_entry_id'], unique=False)
    op.create_index(op.f('ix_payment_plan_ledger_entries_source_charge_id'), 'payment_plan_ledger_entries', ['source_charge_id'], unique=False)
    op.create_index(op.f('ix_payment_plan_ledger_entries_source_transaction_id'), 'payment_plan_ledger_entries', ['source_transaction_id'], unique=False)
    op.create_index('ix_payment_plan_ledger_owner_date', 'payment_plan_ledger_entries', ['owner_id', 'entry_date'], unique=False)
    op.create_index('ix_payment_plan_ledger_plan_date', 'payment_plan_ledger_entries', ['plan_id', 'entry_date'], unique=False)
    op.create_table('payment_plan_transaction_wallet_allocations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('plan_id', sa.Integer(), nullable=False),
    sa.Column('payment_plan_transaction_id', sa.Integer(), nullable=False),
    sa.Column('wallet_id', sa.Integer(), nullable=False),
    sa.Column('amount', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('amount > 0', name='ck_payment_plan_txn_wallet_allocations_amount_positive'),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['payment_plan_transaction_id'], ['payment_plan_transactions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['plan_id'], ['payment_plans.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('payment_plan_transaction_id', 'wallet_id', name='uq_payment_plan_txn_wallet_allocations_wallet')
    )
    op.create_index(op.f('ix_payment_plan_transaction_wallet_allocations_id'), 'payment_plan_transaction_wallet_allocations', ['id'], unique=False)
    op.create_index(op.f('ix_payment_plan_transaction_wallet_allocations_owner_id'), 'payment_plan_transaction_wallet_allocations', ['owner_id'], unique=False)
    op.create_index(op.f('ix_payment_plan_transaction_wallet_allocations_payment_plan_transaction_id'), 'payment_plan_transaction_wallet_allocations', ['payment_plan_transaction_id'], unique=False)
    op.create_index(op.f('ix_payment_plan_transaction_wallet_allocations_plan_id'), 'payment_plan_transaction_wallet_allocations', ['plan_id'], unique=False)
    op.create_index(op.f('ix_payment_plan_transaction_wallet_allocations_wallet_id'), 'payment_plan_transaction_wallet_allocations', ['wallet_id'], unique=False)
    op.add_column('payment_plan_payment_allocations', sa.Column('payment_plan_transaction_id', sa.Integer(), nullable=True))
    op.add_column('payment_plan_payment_allocations', sa.Column('payment_plan_ledger_entry_id', sa.Integer(), nullable=True))
    op.drop_index(op.f('ix_payment_plan_payment_allocations_debt_ledger_entry_id'), table_name='payment_plan_payment_allocations')
    op.drop_index(op.f('ix_payment_plan_payment_allocations_debt_transaction_id'), table_name='payment_plan_payment_allocations')
    op.drop_index(op.f('ix_payment_plan_payment_allocations_wallet_id'), table_name='payment_plan_payment_allocations')
    op.create_index(op.f('ix_payment_plan_payment_allocations_payment_plan_ledger_entry_id'), 'payment_plan_payment_allocations', ['payment_plan_ledger_entry_id'], unique=False)
    op.create_index(op.f('ix_payment_plan_payment_allocations_payment_plan_transaction_id'), 'payment_plan_payment_allocations', ['payment_plan_transaction_id'], unique=False)
    op.drop_constraint(op.f('installment_payment_allocations_wallet_id_fkey'), 'payment_plan_payment_allocations', type_='foreignkey')
    op.drop_constraint(op.f('installment_payment_allocations_debt_transaction_id_fkey'), 'payment_plan_payment_allocations', type_='foreignkey')
    op.drop_constraint(op.f('installment_payment_allocations_debt_ledger_entry_id_fkey'), 'payment_plan_payment_allocations', type_='foreignkey')
    op.create_foreign_key('fk_pp_payment_allocations_plan_ledger_entry_id', 'payment_plan_payment_allocations', 'payment_plan_ledger_entries', ['payment_plan_ledger_entry_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_pp_payment_allocations_plan_transaction_id', 'payment_plan_payment_allocations', 'payment_plan_transactions', ['payment_plan_transaction_id'], ['id'], ondelete='SET NULL')
    op.add_column('payment_plan_payments', sa.Column('payment_plan_charge_id', sa.Integer(), nullable=True))
    op.add_column('payment_plan_payments', sa.Column('payment_plan_ledger_entry_id', sa.Integer(), nullable=True))
    op.drop_index(op.f('ix_payment_plan_payments_debt_charge_id'), table_name='payment_plan_payments')
    op.drop_index(op.f('ix_payment_plan_payments_debt_ledger_entry_id'), table_name='payment_plan_payments')
    op.create_index(op.f('ix_payment_plan_payments_payment_plan_charge_id'), 'payment_plan_payments', ['payment_plan_charge_id'], unique=False)
    op.create_index(op.f('ix_payment_plan_payments_payment_plan_ledger_entry_id'), 'payment_plan_payments', ['payment_plan_ledger_entry_id'], unique=False)
    op.drop_constraint(op.f('fk_payment_plan_payments_debt_ledger_entry_id'), 'payment_plan_payments', type_='foreignkey')
    op.drop_constraint(op.f('fk_payment_plan_payments_debt_charge_id'), 'payment_plan_payments', type_='foreignkey')
    op.create_foreign_key('fk_payment_plan_payments_payment_plan_charge_id', 'payment_plan_payments', 'payment_plan_charges', ['payment_plan_charge_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_payment_plan_payments_payment_plan_ledger_entry_id', 'payment_plan_payments', 'payment_plan_ledger_entries', ['payment_plan_ledger_entry_id'], ['id'], ondelete='SET NULL')
    _backfill_legacy_payment_plan_accounting()
    op.drop_column('payment_plan_payment_allocations', 'debt_transaction_id')
    op.drop_column('payment_plan_payment_allocations', 'debt_ledger_entry_id')
    op.drop_column('payment_plan_payment_allocations', 'wallet_id')
    op.drop_column('payment_plan_payments', 'debt_ledger_entry_id')
    op.drop_column('payment_plan_payments', 'debt_charge_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('payment_plan_payments', sa.Column('debt_charge_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('payment_plan_payments', sa.Column('debt_ledger_entry_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint('fk_payment_plan_payments_payment_plan_ledger_entry_id', 'payment_plan_payments', type_='foreignkey')
    op.drop_constraint('fk_payment_plan_payments_payment_plan_charge_id', 'payment_plan_payments', type_='foreignkey')
    op.create_foreign_key(op.f('fk_payment_plan_payments_debt_charge_id'), 'payment_plan_payments', 'debt_charges', ['debt_charge_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(op.f('fk_payment_plan_payments_debt_ledger_entry_id'), 'payment_plan_payments', 'debt_ledger_entries', ['debt_ledger_entry_id'], ['id'], ondelete='SET NULL')
    op.drop_index(op.f('ix_payment_plan_payments_payment_plan_ledger_entry_id'), table_name='payment_plan_payments')
    op.drop_index(op.f('ix_payment_plan_payments_payment_plan_charge_id'), table_name='payment_plan_payments')
    op.create_index(op.f('ix_payment_plan_payments_debt_ledger_entry_id'), 'payment_plan_payments', ['debt_ledger_entry_id'], unique=False)
    op.create_index(op.f('ix_payment_plan_payments_debt_charge_id'), 'payment_plan_payments', ['debt_charge_id'], unique=False)
    op.drop_column('payment_plan_payments', 'payment_plan_ledger_entry_id')
    op.drop_column('payment_plan_payments', 'payment_plan_charge_id')
    op.add_column('payment_plan_payment_allocations', sa.Column('wallet_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('payment_plan_payment_allocations', sa.Column('debt_ledger_entry_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('payment_plan_payment_allocations', sa.Column('debt_transaction_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint('fk_pp_payment_allocations_plan_transaction_id', 'payment_plan_payment_allocations', type_='foreignkey')
    op.drop_constraint('fk_pp_payment_allocations_plan_ledger_entry_id', 'payment_plan_payment_allocations', type_='foreignkey')
    op.create_foreign_key(op.f('installment_payment_allocations_debt_ledger_entry_id_fkey'), 'payment_plan_payment_allocations', 'debt_ledger_entries', ['debt_ledger_entry_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(op.f('installment_payment_allocations_debt_transaction_id_fkey'), 'payment_plan_payment_allocations', 'debt_transactions', ['debt_transaction_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(op.f('installment_payment_allocations_wallet_id_fkey'), 'payment_plan_payment_allocations', 'wallets', ['wallet_id'], ['id'], ondelete='SET NULL')
    op.drop_index(op.f('ix_payment_plan_payment_allocations_payment_plan_transaction_id'), table_name='payment_plan_payment_allocations')
    op.drop_index(op.f('ix_payment_plan_payment_allocations_payment_plan_ledger_entry_id'), table_name='payment_plan_payment_allocations')
    op.create_index(op.f('ix_payment_plan_payment_allocations_wallet_id'), 'payment_plan_payment_allocations', ['wallet_id'], unique=False)
    op.create_index(op.f('ix_payment_plan_payment_allocations_debt_transaction_id'), 'payment_plan_payment_allocations', ['debt_transaction_id'], unique=False)
    op.create_index(op.f('ix_payment_plan_payment_allocations_debt_ledger_entry_id'), 'payment_plan_payment_allocations', ['debt_ledger_entry_id'], unique=False)
    op.drop_column('payment_plan_payment_allocations', 'payment_plan_ledger_entry_id')
    op.drop_column('payment_plan_payment_allocations', 'payment_plan_transaction_id')
    op.drop_index(op.f('ix_payment_plan_transaction_wallet_allocations_wallet_id'), table_name='payment_plan_transaction_wallet_allocations')
    op.drop_index(op.f('ix_payment_plan_transaction_wallet_allocations_plan_id'), table_name='payment_plan_transaction_wallet_allocations')
    op.drop_index(op.f('ix_payment_plan_transaction_wallet_allocations_payment_plan_transaction_id'), table_name='payment_plan_transaction_wallet_allocations')
    op.drop_index(op.f('ix_payment_plan_transaction_wallet_allocations_owner_id'), table_name='payment_plan_transaction_wallet_allocations')
    op.drop_index(op.f('ix_payment_plan_transaction_wallet_allocations_id'), table_name='payment_plan_transaction_wallet_allocations')
    op.drop_table('payment_plan_transaction_wallet_allocations')
    op.drop_index('ix_payment_plan_ledger_plan_date', table_name='payment_plan_ledger_entries')
    op.drop_index('ix_payment_plan_ledger_owner_date', table_name='payment_plan_ledger_entries')
    op.drop_index(op.f('ix_payment_plan_ledger_entries_source_transaction_id'), table_name='payment_plan_ledger_entries')
    op.drop_index(op.f('ix_payment_plan_ledger_entries_source_charge_id'), table_name='payment_plan_ledger_entries')
    op.drop_index(op.f('ix_payment_plan_ledger_entries_reverses_entry_id'), table_name='payment_plan_ledger_entries')
    op.drop_index(op.f('ix_payment_plan_ledger_entries_plan_id'), table_name='payment_plan_ledger_entries')
    op.drop_index(op.f('ix_payment_plan_ledger_entries_owner_id'), table_name='payment_plan_ledger_entries')
    op.drop_index(op.f('ix_payment_plan_ledger_entries_id'), table_name='payment_plan_ledger_entries')
    op.drop_index(op.f('ix_payment_plan_ledger_entries_financial_event_id'), table_name='payment_plan_ledger_entries')
    op.drop_table('payment_plan_ledger_entries')
    op.drop_index(op.f('ix_payment_plan_transactions_plan_id'), table_name='payment_plan_transactions')
    op.drop_index(op.f('ix_payment_plan_transactions_owner_id'), table_name='payment_plan_transactions')
    op.drop_index(op.f('ix_payment_plan_transactions_id'), table_name='payment_plan_transactions')
    op.drop_table('payment_plan_transactions')
    op.drop_index('ix_payment_plan_charges_plan_id', table_name='payment_plan_charges')
    op.drop_index(op.f('ix_payment_plan_charges_owner_id'), table_name='payment_plan_charges')
    op.drop_index(op.f('ix_payment_plan_charges_id'), table_name='payment_plan_charges')
    op.drop_table('payment_plan_charges')
    # ### end Alembic commands ###
