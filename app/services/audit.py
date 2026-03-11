import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLog, GameRound


class AuditService:
    @staticmethod
    def append(db: Session, actor: str, action: str, object_type: str, object_id: str, details: dict) -> AuditLog:
        last_row = db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1)).scalar_one_or_none()
        prev_hash = last_row.hash_current if last_row else None

        payload = f'{actor}|{action}|{object_type}|{object_id}|{json.dumps(details, sort_keys=True)}|{prev_hash or ""}'
        current_hash = hashlib.sha256(payload.encode()).hexdigest()

        row = AuditLog(
            actor=actor,
            action=action,
            object_type=object_type,
            object_id=object_id,
            details=json.dumps(details, ensure_ascii=False, sort_keys=True),
            hash_prev=prev_hash,
            hash_current=current_hash,
        )
        db.add(row)
        return row


class AdminExportService:
    @staticmethod
    def export_disputed_rounds(db: Session) -> list[dict]:
        rounds = db.execute(select(GameRound).where(GameRound.is_disputed.is_(True)).order_by(GameRound.created_at.desc())).scalars()
        return [
            {
                'round_id': r.id,
                'external_id': r.external_id,
                'user_id': r.user_id,
                'bet_amount': float(r.bet_amount),
                'win_amount': float(r.win_amount),
                'metadata': r.metadata_json,
                'created_at': r.created_at.isoformat(),
            }
            for r in rounds
        ]
