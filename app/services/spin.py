from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import GameRound, LedgerTransaction, TransactionType, User
from app.services.audit import AuditService
from app.services.fraud import check_spin_rate_limit, max_bet_for_level


class SpinError(Exception):
    pass


class SpinService:
    @staticmethod
    def process_spin(
        db: Session,
        user_id: int,
        external_round_id: str,
        bet_amount: Decimal,
        win_amount: Decimal,
    ) -> dict:
        with db.begin():
            user = db.execute(
                select(User).where(User.id == user_id).with_for_update()
            ).scalar_one_or_none()
            if user is None:
                raise SpinError('USER_NOT_FOUND')

            if not check_spin_rate_limit(db, user_id, settings.spin_rate_limit_per_minute):
                raise SpinError('RATE_LIMIT_EXCEEDED')

            if bet_amount > Decimal(max_bet_for_level(user.level)):
                raise SpinError('MAX_BET_EXCEEDED')

            existing_round = db.execute(
                select(GameRound).where(GameRound.external_id == external_round_id)
            ).scalar_one_or_none()
            if existing_round is not None:
                raise SpinError('DUPLICATE_ROUND')

            if Decimal(user.balance) < bet_amount:
                raise SpinError('INSUFFICIENT_FUNDS')

            user.balance = Decimal(user.balance) - bet_amount + win_amount

            game_round = GameRound(
                user_id=user_id,
                external_id=external_round_id,
                bet_amount=bet_amount,
                win_amount=win_amount,
                is_disputed=win_amount > bet_amount * 20,
                metadata_json={'rule': 'auto_dispute_on_high_multiplier'},
            )
            db.add(game_round)
            db.flush()

            db.add(
                LedgerTransaction(
                    user_id=user_id,
                    round_id=game_round.id,
                    transaction_type=TransactionType.BET_DEBIT,
                    amount=-bet_amount,
                    idempotency_key=f'{external_round_id}:{TransactionType.BET_DEBIT.value}',
                )
            )
            if win_amount > 0:
                db.add(
                    LedgerTransaction(
                        user_id=user_id,
                        round_id=game_round.id,
                        transaction_type=TransactionType.SPIN_WIN_CREDIT,
                        amount=win_amount,
                        idempotency_key=f'{external_round_id}:{TransactionType.SPIN_WIN_CREDIT.value}',
                    )
                )

            AuditService.append(
                db,
                actor='system',
                action='SPIN_SETTLED',
                object_type='round',
                object_id=external_round_id,
                details={
                    'user_id': user_id,
                    'bet_amount': str(bet_amount),
                    'win_amount': str(win_amount),
                    'balance_after': str(user.balance),
                },
            )

        return {
            'user_id': user_id,
            'external_round_id': external_round_id,
            'balance': float(user.balance),
        }

    @staticmethod
    def credit_wallet(db: Session, user_id: int, amount: Decimal, tx_type: TransactionType, idempotency_key: str) -> None:
        if tx_type not in {
            TransactionType.DAILY_BONUS_CREDIT,
            TransactionType.MISSION_REWARD_CREDIT,
            TransactionType.CASHBACK_CREDIT,
        }:
            raise SpinError('INVALID_CREDIT_TYPE')

        try:
            with db.begin():
                user = db.execute(select(User).where(User.id == user_id).with_for_update()).scalar_one_or_none()
                if user is None:
                    raise SpinError('USER_NOT_FOUND')

                user.balance = Decimal(user.balance) + amount
                db.add(
                    LedgerTransaction(
                        user_id=user_id,
                        transaction_type=tx_type,
                        amount=amount,
                        idempotency_key=idempotency_key,
                    )
                )
                AuditService.append(
                    db,
                    actor='system',
                    action='WALLET_CREDIT',
                    object_type='user',
                    object_id=str(user_id),
                    details={'amount': str(amount), 'transaction_type': tx_type.value},
                )
        except IntegrityError as exc:
            raise SpinError('DUPLICATE_CREDIT') from exc
