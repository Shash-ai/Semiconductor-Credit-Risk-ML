"""Run scrape → clean → EDA → feature engineering → master modelling dataset.

Stops before ML model training.
"""

from __future__ import annotations

import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE_DIR))

from clean_local_sources import run_cleaning
from feature_engineering import build_master_datasets, engineer_project_features, run_eda
from scrape_web_data import run_all_scrapers


def main() -> None:
    print("=== 1/4 Web scrape ===")
    run_all_scrapers()
    print("=== 2/4 Clean local + scraped sources ===")
    artifacts = run_cleaning()
    print("=== 3/4 EDA ===")
    run_eda(artifacts["projects"], artifacts["panel"])
    print("=== 4/4 Features + master modelling dataset ===")
    feat = engineer_project_features(artifacts["projects"])
    proj, panel, ml = build_master_datasets(feat, artifacts["panel"], artifacts["financials"])
    print("Wrote:")
    print(f"  project-level master {proj.shape}")
    print(f"  project-year panel   {panel.shape}")
    print(f"  ML-ready unscaled    {ml.shape}")
    print("ML training is intentionally not run.")


if __name__ == "__main__":
    main()
