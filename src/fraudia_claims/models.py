from __future__ import annotations

import numpy as np
import pandas as pd


NUMERIC_FEATURES = [
    "monto_reclamado",
    "monto_ratio_suma",
    "dias_desde_inicio_poliza",
    "dias_desde_fin_poliza",
    "dias_entre_ocurrencia_reporte",
    "historial_siniestros_asegurado",
    "frecuencia_asegurado_total",
    "frecuencia_proveedor_total",
    "docs_faltantes",
    "docs_ilegibles",
    "docs_inconsistentes",
    "monto_z_ramo_cobertura",
]


def _fallback_anomaly(frame: pd.DataFrame) -> np.ndarray:
    matrix = frame[NUMERIC_FEATURES].fillna(0).astype(float)
    med = matrix.median()
    mad = (matrix - med).abs().median().replace(0, 1)
    z = ((matrix - med).abs() / mad).clip(0, 12)
    return z.mean(axis=1).to_numpy()


def compute_anomaly_points(features: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    try:
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import RobustScaler
    except Exception:
        IsolationForest = None
        RobustScaler = None

    for ramo, group in features.groupby("ramo"):
        group = group.copy()
        if len(group) < 20:
            anomaly_score = np.zeros(len(group))
        elif IsolationForest is not None and RobustScaler is not None:
            matrix = group[NUMERIC_FEATURES].fillna(0).astype(float)
            scaled = RobustScaler().fit_transform(matrix)
            model = IsolationForest(n_estimators=180, contamination=0.05, random_state=2026)
            model.fit(scaled)
            anomaly_score = -model.decision_function(scaled)
        else:
            anomaly_score = _fallback_anomaly(group)

        p95 = float(np.percentile(anomaly_score, 95)) if len(anomaly_score) else 0.0
        p99 = float(np.percentile(anomaly_score, 99)) if len(anomaly_score) else 0.0
        points = np.where(anomaly_score >= p99, 20, np.where(anomaly_score >= p95, 10, 0))
        rows.append(
            pd.DataFrame(
                {
                    "id_siniestro": group["id_siniestro"].to_numpy(),
                    "anomaly_score": anomaly_score,
                    "score_anomalia": points.astype(int),
                    "ramo": ramo,
                }
            )
        )
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["id_siniestro", "anomaly_score", "score_anomalia", "ramo"])
