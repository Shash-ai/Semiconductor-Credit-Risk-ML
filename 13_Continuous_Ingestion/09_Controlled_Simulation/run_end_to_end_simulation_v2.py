from __future__ import annotations

from pathlib import Path

import run_end_to_end_simulation as core


_ORIGINAL_READ_CSV = core.read_csv


def _read_csv_with_review_object_dtype(path: Path):
    """Keep the synthetic human-review table writable under pandas 3.x.

    Empty review columns are inferred as float64 when the CSV is read because they
    contain only missing values. Pandas 3.x rejects assigning strings into those
    float columns. The controlled simulation needs to populate those review fields
    with synthetic strings, so only the review table is converted to object dtype.
    Production/canonical numeric tables retain their original inferred dtypes.
    """
    df = _ORIGINAL_READ_CSV(path)
    if Path(path).name == "Canonicalization_Review.csv":
        return df.astype(object)
    return df


def main() -> int:
    core.read_csv = _read_csv_with_review_object_dtype
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
