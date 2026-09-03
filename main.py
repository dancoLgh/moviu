"""Entry point for launching the Moviu print desktop app."""

import os
import sys
from pathlib import Path


def packaged_self_test() -> int:
    """Import native runtime dependencies without starting the desktop UI."""

    import ssl

    from moviu_server import app as _app  # noqa: F401

    ssl.create_default_context()
    marker_path = os.environ.get("MOVIU_SELF_TEST_FILE")
    marker_token = os.environ.get("MOVIU_SELF_TEST_TOKEN")
    if marker_path and marker_token:
        Path(marker_path).write_text(marker_token, encoding="ascii")
    return 0


def main() -> None:
    if "--self-test" in sys.argv:
        try:
            exit_code = packaged_self_test()
        except Exception:  # noqa: BLE001
            exit_code = 1
        raise SystemExit(exit_code)

    from moviu_server.app import main as run_desktop_app

    run_desktop_app()


if __name__ == "__main__":
    main()
