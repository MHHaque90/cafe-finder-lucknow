"""Shared dependencies for the Cafe Finder read API.

Dataset access goes through the existing domain loaders and the
centralized path configuration. The browser can never request
arbitrary filesystem paths: only the configured dataset is loaded.
"""

from fastapi import HTTPException

import pandas as pd

from cafe_finder.config import DEFAULT_CSV_PATH
from cafe_finder.search import load_data


def load_dataset() -> pd.DataFrame:
    """Load the processed cafe dataset.

    Raises:
        HTTPException: 500 if the configured dataset is unavailable.
            The filesystem path is never exposed to the client.
    """
    try:
        return load_data(DEFAULT_CSV_PATH)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Dataset unavailable")
    except Exception:
        raise HTTPException(status_code=500, detail="Dataset unavailable")
