from __future__ import annotations

import pandas as pd

import freeze_and_infer_v2 as core


_ORIGINAL_PROJECT_SCORES = core.project_scores
_ORIGINAL_BUILD_LIVE_RAW_FEATURES = core.build_live_raw_features


def _project_scores_without_named_index(z, components):
    """Return PCA scores without duplicating ecosystem_id as both index name and column label."""
    scores = _ORIGINAL_PROJECT_SCORES(z, components)
    scores.index.name = None
    return scores


def _build_live_raw_features_historical_contract(ecosystem: pd.DataFrame) -> pd.DataFrame:
    """Reproduce the Phase-3 telecom indicator exactly enough to match the archived feature matrix.

    The archived Phase-3 matrix shows that NB-IoT/LTE wording alone was not treated as a telecom
    application. Telecom was identified from the application taxonomy (Telecommunications), from
    RF/Radar technology, or—when the application field was empty—from explicit telecom wording.

    This distinction matters for DLI-015: it is tagged IoT in the historical matrix even though its
    project name contains LTE/NB-IoT. Treating every LTE/NB-IoT occurrence as telecom creates one
    extra positive and breaks exact historical reproduction.
    """
    out = _ORIGINAL_BUILD_LIVE_RAW_FEATURES(ecosystem)

    app = ecosystem.get("application", pd.Series("", index=ecosystem.index)).fillna("").astype(str).str.lower().str.strip()
    tech = ecosystem.get("technology", pd.Series("", index=ecosystem.index)).fillna("").astype(str).str.lower().str.strip()
    blob = core.text_blob(ecosystem)

    telecom_from_application = app.str.contains(r"telecommunications|telecom", regex=True, na=False)
    telecom_from_rf_radar = tech.str.contains(r"rf/radar|radio frequency|\bradar\b|\brf\b", regex=True, na=False)

    # For new rows where application taxonomy is unavailable, allow explicit telecom wording as a
    # conservative fallback. Do not classify NB-IoT/LTE alone as telecom when another application
    # taxonomy is already present.
    explicit_telecom_fallback = app.eq("") & blob.str.contains(
        r"telecommunications|telecom|\b5g\b|\b4g\b|broadband|gpon|fttx|satcom|satellite communication",
        regex=True,
        na=False,
    )

    telecom = (telecom_from_application | telecom_from_rf_radar | explicit_telecom_fallback).astype(float)
    out["is_telecom_related"] = telecom.to_numpy()
    return out


def main() -> int:
    core.project_scores = _project_scores_without_named_index
    core.build_live_raw_features = _build_live_raw_features_historical_contract
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
