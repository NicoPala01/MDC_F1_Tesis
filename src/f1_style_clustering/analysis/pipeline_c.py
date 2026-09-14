"""Optional appendix stub: lap-level clustering (Pipeline C).

Pipeline C (cluster individual laps, then map drivers) is reserved for a
future thesis appendix. It is **not** wired into the main CLI path.

TODO: implement per-lap clustering, driver-to-lap majority mapping, and
stability vs Pipeline B — only after Pipeline B is the published main result.
"""

from typing import Any

import pandas as pd


def cluster_laps_pipeline_c(*args: Any, **kwargs: Any) -> pd.DataFrame:
    """Placeholder. Calling this is a no-op for the main thesis pipeline."""
    raise NotImplementedError(
        "Pipeline C (lap-level clustering) is reserved for the thesis appendix "
        "and is not the main clustering path. Use Pipeline B "
        "(typology×session median → driver median → K-means) instead."
    )
