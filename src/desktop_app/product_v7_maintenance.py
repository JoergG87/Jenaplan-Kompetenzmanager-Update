"""Explicit one-shot maintenance entry; ordinary startup never calls execute."""
from pathlib import Path
import os
import subprocess
import sys

from src.core.restore_runtime import RuntimeInstanceLock
from src.security.product_v7 import (
    ProductV7Migration, build_product_v7_service, require_product_v7_scope,
)
from src.security.upgrade_startup import ProductUpgradeStartupGuard


def _command(arguments):
    if getattr(sys, "frozen", False):
        return [sys.executable, *arguments]
    return [sys.executable, "-m", "src.desktop_app.main", *arguments]


def run_product_v7_maintenance(root, *, complete=False):
    root = require_product_v7_scope(Path(root))
    # Load the existing authenticated account/key context only after acquiring
    # the ordinary product instance lock. Never create an account or a key.
    with RuntimeInstanceLock(root) as lock:
        ProductUpgradeStartupGuard(lock)._require_lock()
        service = build_product_v7_service(root, v4_source=True)
        migration = ProductV7Migration(service, fault_hook=lambda boundary:
            print("Wartung: " + boundary, file=sys.stderr, flush=True))
        if not complete:
            migration.execute(lock=lock)
    environment = dict(os.environ)
    if getattr(sys, "frozen", False):
        environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    working_directory = root if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]
    if complete:
        # New process after migration, with no inherited connections or gates.
        migration.complete()
        subprocess.Popen(_command(["--runtime-root", str(root)]),
            close_fds=True, env=environment, cwd=working_directory, start_new_session=True)
        return 0
    return subprocess.run(_command(["--complete-v7-migration", "--runtime-root", str(root)]),
        close_fds=True, env=environment, cwd=working_directory, check=False).returncode
