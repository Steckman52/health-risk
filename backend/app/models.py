from __future__ import annotations
from sqlalchemy import Column, Integer, String, Float, DateTime, text
from sqlalchemy.types import JSON
from app.db import Base

class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    analysis_type = Column(String(32), nullable=False)
    model_name    = Column(String(64), nullable=True)

    risk          = Column(Float, nullable=False)
    risk_category = Column(String(16), nullable=False)

    request_json  = Column(JSON, nullable=True)
    response_json = Column(JSON, nullable=True)
