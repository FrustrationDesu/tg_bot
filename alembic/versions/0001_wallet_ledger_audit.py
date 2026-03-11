"""create wallet, ledger and audit tables

Revision ID: 0001_wallet_ledger_audit
Revises: 
Create Date: 2026-03-11 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001_wallet_ledger_audit'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


transaction_type_enum = sa.Enum(
    'BET_DEBIT',
    'SPIN_WIN_CREDIT',
    'DAILY_BONUS_CREDIT',
    'MISSION_REWARD_CREDIT',
    'CASHBACK_CREDIT',
    name='transaction_type',
)


def upgrade() -> None:
    transaction_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('balance', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'game_rounds',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('external_id', sa.String(length=64), nullable=False),
        sa.Column('bet_amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('win_amount', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('is_disputed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id'),
    )
    op.create_index(op.f('ix_game_rounds_user_id'), 'game_rounds', ['user_id'], unique=False)

    op.create_table(
        'ledger_transactions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('round_id', sa.BigInteger(), nullable=True),
        sa.Column('transaction_type', transaction_type_enum, nullable=False),
        sa.Column('amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False, server_default='COIN'),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['round_id'], ['game_rounds.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key'),
        sa.UniqueConstraint('round_id', 'transaction_type', name='uq_round_tx_type'),
    )
    op.create_index(op.f('ix_ledger_transactions_round_id'), 'ledger_transactions', ['round_id'], unique=False)
    op.create_index(op.f('ix_ledger_transactions_user_id'), 'ledger_transactions', ['user_id'], unique=False)

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('actor', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('object_type', sa.String(length=64), nullable=False),
        sa.Column('object_id', sa.String(length=64), nullable=False),
        sa.Column('details', sa.Text(), nullable=False),
        sa.Column('hash_prev', sa.String(length=64), nullable=True),
        sa.Column('hash_current', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hash_current'),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_ledger_transactions_user_id'), table_name='ledger_transactions')
    op.drop_index(op.f('ix_ledger_transactions_round_id'), table_name='ledger_transactions')
    op.drop_table('ledger_transactions')
    op.drop_index(op.f('ix_game_rounds_user_id'), table_name='game_rounds')
    op.drop_table('game_rounds')
    op.drop_table('users')
    transaction_type_enum.drop(op.get_bind(), checkfirst=True)
