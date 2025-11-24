from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import joblib

# схема признаков по типу анализов
FEATURES: Dict[str, List[str]] = {
    "heart": [
        "age","gender","height","weight","ap_hi","ap_lo",
        "cholesterol","gluc","smoke","alco","active"
    ],
    "diabetes": [
        "Age","Gender","BMI","Chol","TG","HDL","LDL","Cr","BUN"
    ],
}
# приведение к флоту
def _coerce(x) -> float:
    if isinstance(x, bool): return 1.0 if x else 0.0
    if isinstance(x, (int, float, np.number)): return float(x)
    return float(str(x).strip().replace(",", "."))
# ограничения от диких значений
def _clamp(v: float, lo: float, hi: float) -> float:
    v = float(v); return float(min(max(v, lo), hi))
# подготовка признаокв
def vectorize(analysis: str, features: Dict[str, object]) -> Tuple[pd.DataFrame, List[str]]:
    order = FEATURES[analysis]
    missing, row = [], []
    for k in order:
        if k not in features:
            missing.append(k); row.append(np.nan); continue
        try: row.append(_coerce(features[k]))
        except: missing.append(k); row.append(np.nan)
    if missing:
        return pd.DataFrame(columns=order), missing
    d = dict(zip(order, row))

    if analysis == "heart":
        d["age"] = _clamp(d["age"], 1, 45000)
        if d["age"] < 150.0:
            d["age"] = d["age"] * 365.0

        d["height"]=_clamp(d["height"],50,250)
        d["weight"]=_clamp(d["weight"],20,300)
        d["ap_hi"]=_clamp(d["ap_hi"],50,250)
        d["ap_lo"]=_clamp(d["ap_lo"],30,200)
        d["ap_lo"]=min(d["ap_lo"], d["ap_hi"]-1.0)
        d["ap_diff"] = d["ap_hi"] - d["ap_lo"]
        for c in ("cholesterol","gluc"): d[c]=_clamp(round(d[c]),1,3)
        for b in ("smoke","alco","active"): d[b]=1.0 if d[b]>=0.5 else 0.0

    elif analysis == "diabetes":
        d["Age"]=_clamp(d["Age"],1,120)
        d["Gender"]=1.0 if d["Gender"]>=0.5 else 0.0
        d["BMI"]=_clamp(d["BMI"],10,80)
        # Остальные приведены к флоту без жёстких границ

    X = pd.DataFrame([[d[c] for c in order]], columns=order)
    return X, []
# оборачивает модель в класс
class WrappedModel:
    def __init__(self, path: Path):
        self.name = path.stem
        self.path = path
        self.model = joblib.load(path)
        self.pos_idx = 1
        if hasattr(self.model, "classes_"):
            arr = np.asarray(self.model.classes_)
            where = np.where(arr == 1)[0]
            self.pos_idx = int(where[0]) if len(where) else len(arr) - 1

    def proba_pos(self, X: pd.DataFrame) -> float:
        if hasattr(self.model, "predict_proba"):
            p = float(self.model.predict_proba(X)[0][self.pos_idx])
        else:
            p = float(self.model.predict(X)[0])
        return float(min(max(p, 0.0), 1.0))

class Registry:

    def __init__(self):
        base = Path(__file__).resolve().parents[1] / "model"
        self.items: Dict[str, Dict[str, WrappedModel]] = {"heart": {}, "diabetes": {}}

        for analysis in FEATURES.keys():
            folder = base / analysis
            if folder.exists():
                for pattern in ("*.pkl","*.joblib"):
                    for p in sorted(folder.glob(pattern)):
                        self.items[analysis][p.stem] = WrappedModel(p)

        self.defaults: Dict[str, str] = {}
        for analysis in FEATURES.keys():
            names = list(self.items[analysis].keys())
            self.defaults[analysis] = names[0] if names else ""

    def available(self) -> Dict[str, List[str]]:
        return {k: list(v.keys()) for k,v in self.items.items()}

    def default_for(self, analysis: str) -> str:
        return self.defaults.get(analysis, "")

    def predict(self, analysis: str, model_name: str | None, features: Dict[str, object]) -> Tuple[float, str, List[str]]:
        if analysis not in FEATURES:
            raise KeyError(f"unknown analysis_type '{analysis}'")
        if not self.items.get(analysis):
            raise KeyError(f"no models for analysis_type '{analysis}'")
        name = model_name or self.default_for(analysis)
        if name not in self.items[analysis]:
            raise KeyError(f"unknown model '{name}' for analysis_type '{analysis}'")

        X, missing = vectorize(analysis, features)
        if missing:
            return -1.0, name, missing
        prob = self.items[analysis][name].proba_pos(X)
        return prob, name, []
