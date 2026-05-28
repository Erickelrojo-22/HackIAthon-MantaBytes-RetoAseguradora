from __future__ import annotations

import numpy as np
import pandas as pd

from fraudia_claims.utils import normalize_text


def _fallback_similarity(texts: list[str]) -> tuple[np.ndarray, list[int]]:
    normalized = [normalize_text(text) for text in texts]
    first_seen: dict[str, int] = {}
    scores = np.zeros(len(texts))
    matches = [-1 for _ in texts]
    for idx, text in enumerate(normalized):
        if text in first_seen:
            scores[idx] = 1.0
            matches[idx] = first_seen[text]
        else:
            first_seen[text] = idx
    return scores, matches


def compute_text_similarity(features: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except Exception:
        TfidfVectorizer = None
        cosine_similarity = None

    for ramo, group in features.groupby("ramo"):
        group = group.reset_index(drop=True).copy()
        texts = group["descripcion"].fillna("").astype(str).tolist()
        if len(group) < 2:
            max_sim = np.zeros(len(group))
            match_idx = [-1 for _ in range(len(group))]
        elif TfidfVectorizer is not None and cosine_similarity is not None:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
            matrix = vectorizer.fit_transform(texts)
            similarity = cosine_similarity(matrix)
            np.fill_diagonal(similarity, 0)
            match_idx = similarity.argmax(axis=1).tolist()
            max_sim = similarity.max(axis=1)
        else:
            max_sim, match_idx = _fallback_similarity(texts)

        points = np.where(max_sim > 0.85, 8, np.where(max_sim >= 0.70, 4, 0))
        if "escenario_riesgo" in group.columns:
            min_yellow = (max_sim > 0.85) & (group["escenario_riesgo"].fillna("normal").astype(str).to_numpy() != "normal")
        else:
            min_yellow = np.zeros(len(group), dtype=bool)
        matched_claim = []
        for idx in match_idx:
            if idx is None or idx < 0:
                matched_claim.append("")
            else:
                matched_claim.append(str(group.loc[int(idx), "id_siniestro"]))
        rows.append(
            pd.DataFrame(
                {
                    "id_siniestro": group["id_siniestro"],
                    "similitud_narrativa": max_sim,
                    "siniestro_similar": matched_claim,
                    "score_nlp": points.astype(int),
                    "nlp_min_amarillo": min_yellow.astype(bool),
                    "ramo": ramo,
                }
            )
        )
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["id_siniestro", "similitud_narrativa", "siniestro_similar", "score_nlp", "nlp_min_amarillo", "ramo"])
