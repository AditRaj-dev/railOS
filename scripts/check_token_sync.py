#!/usr/bin/env python3
"""Check that packages/design-tokens/dist matches the distributed copies in apps."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "packages" / "design-tokens" / "dist"
CSS_DIST = DIST_DIR / "railos_tokens.css"
DART_DIST = DIST_DIR / "railos_tokens.dart"

CSS_APP = REPO_ROOT / "apps" / "control-center" / "src" / "app" / "railos_tokens.css"
DART_APP = REPO_ROOT / "apps" / "field-app" / "lib" / "theme" / "railos_tokens.dart"

def main():
    errors = []
    if not CSS_DIST.exists():
        errors.append(f"Missing {CSS_DIST}")
    if not DART_DIST.exists():
        errors.append(f"Missing {DART_DIST}")

    if not CSS_APP.exists():
        errors.append(f"Missing {CSS_APP}")
    elif CSS_DIST.exists() and CSS_DIST.read_text(encoding="utf-8") != CSS_APP.read_text(encoding="utf-8"):
        errors.append(f"Drift detected between {CSS_DIST} and {CSS_APP}")

    if not DART_APP.exists():
        errors.append(f"Missing {DART_APP}")
    elif DART_DIST.exists() and DART_DIST.read_text(encoding="utf-8") != DART_APP.read_text(encoding="utf-8"):
        errors.append(f"Drift detected between {DART_DIST} and {DART_APP}")

    if errors:
        print("FAIL: Design token distribution check failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    print("OK: Design tokens are in sync across apps/control-center and apps/field-app.")

if __name__ == "__main__":
    main()
