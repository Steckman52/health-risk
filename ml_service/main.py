from __future__ import annotations
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .model_loader import Registry

app = FastAPI(title="Unified ML (heart + diabetes)")
registry: Registry | None = None

class PredictIn(BaseModel):
    analysis_type: str                 # heart или diabetes
    features: Dict[str, Any]           # поля по схеме analysis_type
    model: Optional[str] = None        # имя модели

class PredictOut(BaseModel):
    analysis_type: str
    model: str
    risk: float
    risk_category: str
    recommendation: Optional[str] = None

def bucket(p: float) -> str:
    if p < 0.33: return "low"
    if p < 0.66: return "medium"
    return "high"

@app.on_event("startup")
def _startup():
    global registry
    registry = Registry()

@app.get("/health")
def health():
    return {
        "status":"ok",
        "models": registry.available(),
        "defaults": {k: registry.default_for(k) for k in ("heart","diabetes")}
    }

@app.post("/predict", response_model=PredictOut)
def predict(body: PredictIn):
    analysis = body.analysis_type.lower().strip()
    try:
        prob, used, missing = registry.predict(analysis, body.model, body.features)
    except KeyError as e:
        raise HTTPException(400, str(e))
    if missing:
        raise HTTPException(400, f"Отсутствуют признаки: {', '.join(missing)}")

    cat = bucket(prob)
    rec = ("Низкий риск. Поддерживайте ЗОЖ."
           if cat=="low" else
           "Умеренный риск. Рекомендуется контроль."
           if cat=="medium" else
           "Высокий риск! Желательна очная консультация.")
    return PredictOut(analysis_type=analysis, model=used, risk=prob, risk_category=cat, recommendation=rec)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)
