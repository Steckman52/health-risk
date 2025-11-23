from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List

import httpx
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from config import settings
from app.db import Base, engine, get_db
from app.models import PredictionLog

app = FastAPI(title=getattr(settings, "APP_NAME", "Health Risk Backend"))
router = APIRouter(prefix="/api/v1")
log = logging.getLogger("uvicorn.error")

ML_HEART_URL = getattr(settings, "ML_HEART_URL", None) or getattr(settings, "ML_BASE_URL", "http://127.0.0.1:8001")
ML_DIAB_URL  = getattr(settings, "ML_DIAB_URL",  None) or getattr(settings, "ML_BASE_URL", "http://127.0.0.1:8001")
ML_PREDICT_PATH = getattr(settings, "ML_PREDICT_PATH", "/predict")
ML_TIMEOUT_SECONDS = int(getattr(settings, "ML_TIMEOUT_SECONDS", 5))

RISK_RU = {"low": "низкий", "medium": "умеренный", "high": "высокий"}

#  схемы ввода/вывода
class PredictRequest(BaseModel):
    analysis_type: str
    features: Dict[str, Any]
    model: Optional[str] = None

class PredictResponse(BaseModel):
    analysis_type: str
    model: Optional[str]
    risk: float
    risk_category: str
    risk_category_ru: str
    recommendation: Optional[str] = None

class PredictionLogOut(BaseModel):
    id: int
    created_at: Optional[str]
    analysis_type: str
    model_name: Optional[str]
    risk: float
    risk_category: str
    risk_category_ru: str

#  утилита для нормального выбора мльки
def _ml_endpoint(analysis_type: str) -> str:
    at = analysis_type.lower().strip()
    if at == "heart":
        return f"{ML_HEART_URL}{ML_PREDICT_PATH}"
    if at == "diabetes":
        return f"{ML_DIAB_URL}{ML_PREDICT_PATH}"
    raise HTTPException(status_code=400, detail="unsupported analysis_type")

# создает таблицу в бл чтоб история была
@app.on_event("startup")
async def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    log.info("DB schema ensured. ML: heart=%s, diabetes=%s", ML_HEART_URL, ML_DIAB_URL)

# проверяет что все живое запустилось и не упало, доступно ли бд, подлкючен ли мл
@app.get("/health")
async def health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        db.execute(sql_text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok",
        "db": "ok" if db_ok else "error",
        "ml": {
            "heart": f"{ML_HEART_URL}{ML_PREDICT_PATH}",
            "diabetes": f"{ML_DIAB_URL}{ML_PREDICT_PATH}",
            "timeout_sec": ML_TIMEOUT_SECONDS,
        },
    }

# предсказание с логированием
@router.post("/predict", response_model=PredictResponse)
async def predict(payload: PredictRequest, db: Session = Depends(get_db)) -> Any:
    ml_url = _ml_endpoint(payload.analysis_type)

    # вызов ML
    try:
        async with httpx.AsyncClient(timeout=ML_TIMEOUT_SECONDS) as client:
            r = await client.post(ml_url, json=payload.model_dump())
        r.raise_for_status()
        ml_resp: Dict[str, Any] = r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"ML call failed: {e}")

    # нормализация ответа
    risk = float(ml_resp.get("risk", 0.0))
    cat_en = str(ml_resp.get("risk_category", "")).lower()
    cat_ru = RISK_RU.get(cat_en, cat_en or "")
    recommendation = ml_resp.get("recommendation")
    model_used = ml_resp.get("model") or payload.model

    # запись в БД
    try:
        row = PredictionLog(
            analysis_type=payload.analysis_type.lower().strip(),
            model_name=model_used,
            risk=risk,
            risk_category=cat_en,
            request_json=payload.model_dump(),
            response_json=ml_resp,
        )
        db.add(row)
        db.commit()
    except Exception as e:
        db.rollback()
        log.warning("DB log write failed: %s", e)

    return PredictResponse(
        analysis_type=payload.analysis_type.lower().strip(),
        model=model_used,
        risk=risk,
        risk_category=cat_en,
        risk_category_ru=cat_ru,
        recommendation=recommendation,
    )

#  история (для бота)
@router.get("/logs", response_model=List[PredictionLogOut])
async def list_logs(
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> Any:
    rows = (
        db.query(PredictionLog)
        .order_by(PredictionLog.id.desc())
        .limit(limit)
        .all()
    )
    out: List[PredictionLogOut] = []
    for r in rows:
        out.append(
            PredictionLogOut(
                id=r.id,
                created_at=str(r.created_at) if r.created_at else None,
                analysis_type=r.analysis_type,
                model_name=r.model_name,
                risk=float(r.risk),
                risk_category=r.risk_category,
                risk_category_ru=RISK_RU.get(r.risk_category, r.risk_category),
            )
        )
    return out

app.include_router(router)
