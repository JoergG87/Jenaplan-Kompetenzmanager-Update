#!/usr/bin/env python3
"""German interactive provisioning flow for an external encrypted keypair."""

from __future__ import annotations

from datetime import UTC, datetime
import getpass
import os
from pathlib import Path
import re
import sys
from typing import Callable, TextIO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.generate_support_keypair import generate_keypair


KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
DEFAULT_KEY_DIRECTORY = Path.home() / "Documents" / "Jenaplan-Support-Reset" / "keys"


class ProvisioningError(ValueError):
    pass


def run_interactive(
    *,
    input_fn: Callable[[str], str] = input,
    getpass_fn: Callable[[str], str] = getpass.getpass,
    output: TextIO = sys.stdout,
    now_fn: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> int:
    print(
        "ACHTUNG: Der private Support-Schlüssel kann kurz gültige Reset-Codes signieren. "
        "Er muss verschlüsselt, getrennt von App, Repository und Pilotpaketen aufbewahrt werden.",
        file=output,
    )
    raw_directory = input_fn(f"Externes Schlüsselverzeichnis [{DEFAULT_KEY_DIRECTORY}]: ").strip()
    directory = Path(raw_directory).expanduser() if raw_directory else DEFAULT_KEY_DIRECTORY
    if not directory.is_absolute():
        directory = Path.cwd() / directory
    if directory.is_symlink():
        raise ProvisioningError("Das Ziel ist kein sicherer Schlüsselordner.")
    directory = directory.resolve(strict=False)
    if _inside_repository(directory):
        raise ProvisioningError("Schlüssel dürfen nicht innerhalb eines Repositorys liegen.")
    if directory.exists() and not directory.is_dir():
        raise ProvisioningError("Das Ziel ist kein sicherer Schlüsselordner.")
    if not directory.exists():
        confirm = input_fn(f"Ordner {directory} mit Rechten 700 anlegen? [JA/nein]: ").strip()
        if confirm != "JA":
            print("Abgebrochen. Es wurde kein Schlüssel erzeugt.", file=output)
            return 2
        directory.mkdir(parents=True, mode=0o700)
    if os.name == "posix":
        os.chmod(directory, 0o700)

    key_id = input_fn("Eindeutige key_id (z. B. support-2026-a): ").strip()
    if not KEY_ID_PATTERN.fullmatch(key_id):
        raise ProvisioningError("Die key_id ist ungültig.")
    private_path = directory / f"jenaplan-support-{key_id}-private.pem"
    public_path = directory / f"jenaplan-support-{key_id}-public.json"
    first = getpass_fn("Starke Passphrase (mindestens 20 Zeichen): ").encode("utf-8")
    second = getpass_fn("Passphrase sicher wiederholen: ").encode("utf-8")
    if first != second:
        first = second = b""
        raise ProvisioningError("Die Passphrasen stimmen nicht überein.")
    descriptor = generate_keypair(
        private_path=private_path,
        public_path=public_path,
        key_id=key_id,
        passphrase=first,
        created_at=now_fn(),
    )
    first = second = b""
    print("\nVerschlüsseltes Support-Schlüsselpaar erzeugt.", file=output)
    print(f"  Privater Schlüssel (600): {private_path}", file=output)
    print(f"  Öffentliche Beschreibung (600): {public_path}", file=output)
    print(f"  key_id: {descriptor['key_id']}", file=output)
    print(f"  Erstellt: {descriptor['created_at']}", file=output)
    print(f"  Vorgesehener Status: {descriptor['intended_status']}", file=output)
    print(f"  Fingerprint (SHA-256): {descriptor['fingerprint_sha256']}", file=output)
    print(
        "Die Registry wurde nicht verändert. Geben Sie ausschließlich die öffentliche "
        "Beschreibung und den Fingerprint zur getrennten Produktprüfung weiter.",
        file=output,
    )
    return 0


def _inside_repository(path: Path) -> bool:
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return True
    return False


def main() -> int:
    if len(sys.argv) != 1:
        print("Dieses Werkzeug übernimmt keine Passphrasen als Argumente.", file=sys.stderr)
        return 2
    try:
        return run_interactive()
    except (ProvisioningError, ValueError, OSError) as exc:
        print(f"Sicherer Abbruch: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nAbgebrochen. Es wurde kein Schlüssel erzeugt.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
