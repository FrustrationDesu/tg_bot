import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TransactionType(str, enum.Enum):
    BET_DEBIT = 'BET_DEBIT'
    SPIN_WIN_CREDIT = 'SPIN_WIN_CREDIT'
    DAILY_BONUS_CREDIT = 'DAILY_BONUS_CREDIT'
    MISSION_REWARD_CREDIT = 'MISSION_REWARD_CREDIT'
    CASHBACK_CREDIT = 'CASHBACK_CREDIT'


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    balance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class GameRound(Base):
    __tablename__ = 'game_rounds'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    bet_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    win_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    is_disputed: Mapped[bool] = mapped_column(default=False, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    transactions: Mapped[list['LedgerTransaction']] = relationship(back_populates='round')


class LedgerTransaction(Base):
    __tablename__ = 'ledger_transactions'
    __table_args__ = (
        UniqueConstraint('round_id', 'transaction_type', name='uq_round_tx_type'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    round_id: Mapped[int | None] = mapped_column(ForeignKey('game_rounds.id'), nullable=True, index=True)
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType, name='transaction_type'), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default='COIN')
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    round: Mapped[GameRound | None] = relationship(back_populates='transactions')


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    hash_prev: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hash_current: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
