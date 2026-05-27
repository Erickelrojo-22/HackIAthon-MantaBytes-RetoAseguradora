from __future__ import annotations

from datetime import datetime, timezone

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

CATEGORICAL_FEATURES = [
    "ramo",
    "cobertura",
    "sucursal",
    "estado",
    "canal_venta",
    "segmento",
    "ciudad_asegurado",
    "ciudad_proveedor",
    "tipo",
]

BOOLEAN_FEATURES = [
    "documentos_completos",
    "lista_restrictiva_proveedor",
    "lista_restrictiva_asegurado",
    "mora_actual",
    "solo_rc",
    "tercero_identificado",
    "accidente_madrugada",
    "dinamica_imposible",
    "relato_ilogico",
    "adulteracion_documental",
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


def _empty_supervised(features: pd.DataFrame, status: str, reason: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    scores = pd.DataFrame(
        {
            "id_siniestro": features.get("id_siniestro", pd.Series(dtype=str)),
            "probabilidad_modelo": np.zeros(len(features)),
            "score_modelo": np.zeros(len(features), dtype=int),
        }
    )
    metrics = pd.DataFrame(
        [
            {
                "modelo": "RandomForestClassifier",
                "metrica": "status",
                "valor": status,
                "detalle": reason,
                "fecha_generacion": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )
    return scores, metrics


def _model_points(probability: np.ndarray) -> np.ndarray:
    return np.where(probability >= 0.80, 15, np.where(probability >= 0.60, 10, np.where(probability >= 0.40, 5, 0)))


def compute_supervised_points(features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train a demo supervised model with the synthetic label and return traceable points.

    The label is intentionally synthetic; metrics are useful to compare runs, not to
    claim production antifraud performance.
    """
    if "etiqueta_fraude_simulada" not in features.columns:
        return _empty_supervised(features, "skipped", "No existe etiqueta_fraude_simulada.")

    label = features["etiqueta_fraude_simulada"].fillna(0).astype(int)
    if len(features) < 50 or label.nunique() < 2:
        return _empty_supervised(features, "skipped", "Dataset insuficiente o con una sola clase.")

    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.impute import SimpleImputer
        from sklearn.metrics import (
            accuracy_score,
            confusion_matrix,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder
    except Exception as exc:
        return _empty_supervised(features, "fallback", f"scikit-learn no disponible: {exc}")

    numeric = [col for col in NUMERIC_FEATURES + BOOLEAN_FEATURES if col in features.columns]
    categorical = [col for col in CATEGORICAL_FEATURES if col in features.columns]
    model_frame = features[numeric + categorical].copy()
    for col in BOOLEAN_FEATURES:
        if col in model_frame.columns:
            model_frame[col] = model_frame[col].fillna(False).astype(bool).astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        model_frame,
        label,
        test_size=0.25,
        random_state=2026,
        stratify=label,
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", SimpleImputer(strategy="median"), numeric),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                categorical,
            ),
        ],
        remainder="drop",
    )
    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=180,
                    min_samples_leaf=4,
                    class_weight="balanced",
                    random_state=2026,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    pipeline.fit(X_train, y_train)
    test_probability = pipeline.predict_proba(X_test)[:, 1]
    test_pred = (test_probability >= 0.50).astype(int)
    all_probability = pipeline.predict_proba(model_frame)[:, 1]
    matrix = confusion_matrix(y_test, test_pred, labels=[0, 1])
    tn, fp, fn, tp = [int(value) for value in matrix.ravel()]
    generated_at = datetime.now(timezone.utc).isoformat()
    metric_rows = [
        ("status", "ok", "Modelo entrenado con etiqueta sintética; no representa validación legal ni productiva."),
        ("accuracy", float(accuracy_score(y_test, test_pred)), "Proporción de predicciones correctas en holdout sintético."),
        ("precision", float(precision_score(y_test, test_pred, zero_division=0)), "De los casos marcados como fraude simulado, cuántos lo eran."),
        ("recall", float(recall_score(y_test, test_pred, zero_division=0)), "De los fraudes simulados, cuántos fueron detectados."),
        ("f1", float(f1_score(y_test, test_pred, zero_division=0)), "Balance entre precision y recall."),
        ("auc_roc", float(roc_auc_score(y_test, test_probability)), "Separación de clases sobre etiqueta sintética."),
        ("matriz_confusion_tn", tn, "Verdaderos negativos en holdout sintético."),
        ("matriz_confusion_fp", fp, "Falsos positivos en holdout sintético."),
        ("matriz_confusion_fn", fn, "Falsos negativos en holdout sintético."),
        ("matriz_confusion_tp", tp, "Verdaderos positivos en holdout sintético."),
    ]
    metrics = pd.DataFrame(
        [
            {
                "modelo": "RandomForestClassifier",
                "metrica": name,
                "valor": value,
                "detalle": detail,
                "fecha_generacion": generated_at,
            }
            for name, value, detail in metric_rows
        ]
    )
    scores = pd.DataFrame(
        {
            "id_siniestro": features["id_siniestro"].to_numpy(),
            "probabilidad_modelo": all_probability.round(6),
            "score_modelo": _model_points(all_probability).astype(int),
        }
    )
    return scores, metrics
