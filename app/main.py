from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import SpinRequest, SpinResponse
from app.db.database import get_db
from app.services.audit import AdminExportService
from app.services.spin import SpinError, SpinService

app = FastAPI(title='tg_bot wallet service')


@app.post('/spin', response_model=SpinResponse)
def spin(payload: SpinRequest, db: Session = Depends(get_db)) -> SpinResponse:
    try:
        result = SpinService.process_spin(
            db=db,
            user_id=payload.user_id,
            external_round_id=payload.external_round_id,
            bet_amount=payload.bet_amount,
            win_amount=payload.win_amount,
        )
        return SpinResponse(**result)
    except SpinError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get('/admin/disputed-rounds')
def export_disputed_rounds(db: Session = Depends(get_db)) -> list[dict]:
    return AdminExportService.export_disputed_rounds(db)
