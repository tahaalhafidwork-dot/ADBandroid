"""Import legacy data into the lab without modifying the legacy sources.

Examples::

    python scripts/import_legacy_data.py --list
    python scripts/import_legacy_data.py --source real_estate_ai_pipeline/output/aqarati_50_results.json --mode copy
    python scripts/import_legacy_data.py --source real_estate_ai_pipeline/output --mode reference
"""

from __future__ import annotations

import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend import legacy_import, paths  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="legacy file or directory to import")
    parser.add_argument(
        "--mode",
        choices=legacy_import.MODES,
        default=legacy_import.COPY,
        help="copy the payload into data/legacy, or only reference it",
    )
    parser.add_argument("--name", help="name used for the import inside data/legacy")
    parser.add_argument(
        "--allow-pii",
        action="store_true",
        help="import files that look like personal data (off by default)",
    )
    parser.add_argument("--list", action="store_true", help="list the known legacy sources")
    args = parser.parse_args()

    if args.list or not args.source:
        print("Known legacy sources (read-only):")
        for root in legacy_import.known_legacy_sources():
            print("  {0}".format(paths.relative_to_repo(root)))
        if not args.source:
            return 0

    source = paths.repo_path(args.source)
    result = legacy_import.import_source(
        source,
        mode=args.mode,
        allow_pii=args.allow_pii,
        name=args.name,
    )

    print("Imported {0} file(s) in '{1}' mode".format(len(result.entries), result.mode))
    for entry in result.entries:
        destination = entry.destination or "(reference only)"
        print("  {0} -> {1}".format(entry.source, destination))
    for skipped in result.skipped:
        print("  skipped {0}: {1}".format(skipped["source"], skipped["reason"]))
    print("Manifest: {0}".format(paths.relative_to_repo(paths.data_path("imports", "manifest.json"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
