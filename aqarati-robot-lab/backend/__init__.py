"""Aqarati Robot AI Lab backend package.

The package is a scaffold: it owns the project layout, the path rules and the
legacy import mechanism. The control interface and the processing engine are
intentionally not implemented yet.
"""

from . import config, legacy_import, paths  # noqa: F401

__all__ = ["config", "legacy_import", "paths"]
__version__ = "0.1.0"
