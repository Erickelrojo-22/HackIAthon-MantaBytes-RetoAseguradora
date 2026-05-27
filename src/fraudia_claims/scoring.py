from __future__ import annotations

import pandas as pd

from fraudia_claims.config import LEVELS
from fraudia_claims.features import build_feature_frame
from fraudia_claims.models import compute_anomaly_points, compute_supervised_points
from fraudia_claims.nlp import compute_text_similarity
from fraudia_claims.rules import apply_rules


def level_from_score(score: int | float) -> str:
    score = int(round(float(score)))
    if score <= LEVELS["Verde"]["max"]:
        return "Verde"
    if score <= LEVELS["Amarillo"]["max"]:
        return "Amarillo"
    return "Rojo"


def action_from_level(level: str) -> str:
    return LEVELS.get(level, LEVELS["Verde"])["accion"]


def _build_explanations(alerts: pd.DataFrame) -> dict[str, str]:
    if alerts.empty:
        return {}
    explanations: dict[str, str] = {}
    ordered = alerts.sort_values(["id_siniestro", "puntos"], ascending=[True, False])
    for claim_id, group in ordered.groupby("id_siniestro"):
        top = group.head(3)
        parts = [f"{row.descripcion} ({row.puntos} pts)" for row in top.itertuples()]
        explanations[str(claim_id)] = " | ".join(parts)
    return explanations


def _model_alerts(anomaly: pd.DataFrame, nlp: pd.DataFrame, supervised: pd.DataFrame, offset: int = 0) -> pd.DataFrame:
    rows: list[dict] = []
    for row in anomaly[anomaly["score_anomalia"] > 0].itertuples():
        rows.append(
            {
                "id_siniestro": row.id_siniestro,
                "codigo": "IA-01",
                "categoria": "Anomalia",
                "severidad": "Alta" if row.score_anomalia == 20 else "Media",
                "puntos": int(row.score_anomalia),
                "descripcion": "Caso fuera del comportamiento numerico esperado para su ramo.",
                "evidencia": f"Score de rareza {float(row.anomaly_score):.4f}.",
                "es_critica": False,
            }
        )
    for row in nlp[nlp["score_nlp"] > 0].itertuples():
        rows.append(
            {
                "id_siniestro": row.id_siniestro,
                "codigo": "RF-07",
                "categoria": "Narrativa",
                "severidad": "Alta" if row.score_nlp >= 8 else "Media",
                "puntos": int(row.score_nlp),
                "descripcion": "Narrativa muy similar a otro reclamo del mismo ramo.",
                "evidencia": f"Similitud {float(row.similitud_narrativa):.2%} con {row.siniestro_similar}.",
                "es_critica": False,
            }
        )
    for row in supervised[supervised["score_modelo"] > 0].itertuples():
        rows.append(
            {
                "id_siniestro": row.id_siniestro,
                "codigo": "IA-02",
                "categoria": "Modelo supervisado",
                "severidad": "Alta" if row.score_modelo >= 15 else "Media",
                "puntos": int(row.score_modelo),
                "descripcion": "Modelo supervisado detecta probabilidad elevada sobre etiqueta sintetica.",
                "evidencia": f"Probabilidad demo {float(row.probabilidad_modelo):.1%}.",
                "es_critica": False,
            }
        )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame.insert(0, "id_alerta", [f"ALT{i + offset:06d}" for i in range(1, len(frame) + 1)])
    return frame


def score_claims(tables: dict[str, pd.DataFrame], include_metrics: bool = False):
    features = build_feature_frame(tables)
    rules_summary, rule_alerts = apply_rules(features)
    anomaly = compute_anomaly_points(features)
    nlp = compute_text_similarity(features)
    supervised, metrics = compute_supervised_points(features)

    scores = (
        features[["id_siniestro", "ramo", "cobertura", "id_asegurado", "id_proveedor", "sucursal", "monto_reclamado"]]
        .merge(rules_summary, on="id_siniestro", how="left")
        .merge(anomaly[["id_siniestro", "anomaly_score", "score_anomalia"]], on="id_siniestro", how="left")
        .merge(nlp[["id_siniestro", "similitud_narrativa", "siniestro_similar", "score_nlp"]], on="id_siniestro", how="left")
        .merge(supervised[["id_siniestro", "probabilidad_modelo", "score_modelo"]], on="id_siniestro", how="left")
    )
    scores[["score_reglas", "score_anomalia", "score_nlp", "score_modelo"]] = scores[
        ["score_reglas", "score_anomalia", "score_nlp", "score_modelo"]
    ].fillna(0).astype(int)
    scores["probabilidad_modelo"] = scores["probabilidad_modelo"].fillna(0).astype(float)
    scores["regla_critica"] = scores["regla_critica"].fillna(False).astype(bool)
    scores["score_final"] = (
        scores["score_reglas"].clip(upper=60) + scores["score_anomalia"] + scores["score_nlp"] + scores["score_modelo"]
    ).clip(upper=100)
    scores.loc[scores["regla_critica"] & (scores["score_final"] < 76), "score_final"] = 76
    scores["score_final"] = scores["score_final"].astype(int)
    scores["nivel_riesgo"] = scores["score_final"].map(level_from_score)
    scores["accion_sugerida"] = scores["nivel_riesgo"].map(action_from_level)

    offset = 0 if rule_alerts.empty else len(rule_alerts)
    generated_alerts = _model_alerts(anomaly, nlp, supervised, offset=offset)
    alerts = pd.concat([rule_alerts, generated_alerts], ignore_index=True)
    explanations = _build_explanations(alerts)
    scores["explicacion_resumen"] = scores["id_siniestro"].map(explanations).fillna("Sin alertas materiales; mantener flujo normal con controles habituales.")
    scores = scores.sort_values("score_final", ascending=False).reset_index(drop=True)
    alerts = alerts.reset_index(drop=True)
    if include_metrics:
        return scores, alerts, metrics
    return scores, alerts
