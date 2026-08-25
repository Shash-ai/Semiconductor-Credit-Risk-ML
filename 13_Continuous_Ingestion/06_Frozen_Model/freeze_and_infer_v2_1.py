from __future__ import annotations

import freeze_and_infer_v2 as core


_ORIGINAL_PROJECT_SCORES = core.project_scores


def _project_scores_without_named_index(z, components):
    """Return PCA scores without duplicating ecosystem_id as both index name and column label.

    Phase 13E V2 intentionally keeps ecosystem_id as a normal column after projection. Pandas
    treats a merge key as ambiguous when the same label is also the index level name. Clearing
    the index name preserves row alignment while making subsequent merges unambiguous.
    """
    scores = _ORIGINAL_PROJECT_SCORES(z, components)
    scores.index.name = None
    return scores


def main() -> int:
    core.project_scores = _project_scores_without_named_index
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
