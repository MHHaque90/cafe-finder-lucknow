"""Minimal path configuration for cafe-finder.

Provides default data directory paths. Can be overridden via
CAFE_FINDER_DATA_DIR environment variable.

This module uses ``pathlib.Path`` and the standard library ``os``
module only.  It introduces no side effects at import time and
avoids creating directories automatically.

The default base directory is ``Path("data")`` — i.e. a ``data``
directory relative to the current working directory.  Set the
``CAFE_FINDER_DATA_DIR`` environment variable to override it:

    >>> import os, pathlib
    >>> os.environ["CAFE_FINDER_DATA_DIR"] = "/path/to/data"
    >>> from cafe_finder import config
    >>> config.DATA_DIR
    PosixPath('/path/to/data')

.. env:: CAFE_FINDER_DATA_DIR
    Base data directory.  Relative paths are resolved relative to the
    current working directory when the variable is not set.

"""

import os
from pathlib import Path

#: Default CSV path.  Equivalent to ``Path("data/processed/lucknow_cafes.csv")``.
DEFAULT_CSV_PATH = Path("data/processed/lucknow_cafes.csv")

#: Default output directory for visualizations.  Equivalent to
#: ``Path("data/processed/visualizations")``.
DEFAULT_OUTPUT_DIR = Path("data/processed/visualizations")

#: Base data directory.  Defaults to ``Path("data")`` — a ``data``
#: directory relative to the current working directory.  Can be
#: overridden with the ``CAFE_FINDER_DATA_DIR`` environment variable.
#:
#: When the environment variable is not set the value is equivalent
#: to ``Path("data")``, so all existing behaviour is preserved
#: without any configuration.
DATA_DIR = Path(os.environ["CAFE_FINDER_DATA_DIR"]) if "CAFE_FINDER_DATA_DIR" in os.environ else Path("data")

#: ``DATA_DIR / "raw" ``
RAW_DIR = DATA_DIR / "raw"

#: ``DATA_DIR / "processed" ``
PROCESSED_DIR = DATA_DIR / "processed"

#: ``RAW_DIR / "snapshots" ``
SNAPSHOTS_RAW_DIR = RAW_DIR / "snapshots"

#: ``PROCESSED_DIR / "snapshots" ``
SNAPSHOTS_PROCESSED_DIR = PROCESSED_DIR / "snapshots"