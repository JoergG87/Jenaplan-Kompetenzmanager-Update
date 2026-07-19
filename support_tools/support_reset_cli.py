#!/usr/bin/env python3
"""German interactive offline operator flow for one bound support reset."""

from __future__ import annotations

import base64
import binascii
import getpass
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
import re
import stat
import sys
from typing import Callable, TextIO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.security.support_reset import SupportResetTokenCodec
from tools.generate_support_reset import generate_token_from_request_bytes


ALLOWED_LIFETIMES = (15, 30, 60, 120)
PUBLIC_DESCRIPTOR_FIELDS = {
    "format_version",
    "algorithm",
    "key_id",
    "public_key",
    "created_at",
    "intended_status",
    "fingerprint_sha256",
}
MAX_INPUT_BYTES = 4096
MAX_PASSPHRASE_BYTES = 4096
KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class OperatorInputError(ValueError):
    """Expected, non-secret operator or file validation error."""


def run_interactive(
    *,
    input_fn: Callable[[str], str] = input,
    getpass_fn: Callable[[str], str] = getpass.getpass,
    output: TextIO = sys.stdout,
    error: TextIO = sys.stderr,
    now_fn: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> int:
    del error  # all expected messages are intentionally generic on stdout
    _write(
        output,
        "Dieses Werkzeug erzeugt keinen Benutzerzugang und kein Passwort. "
        "Es signiert ausschließlich eine technische, kurz gültige Rücksetzanforderung.",
    )
    _write(output, "Es liest keine Schülerdaten, Datenbanken, Backups oder Dokumente.")
    request_bytes = _read_request(input_fn, output)
    request = SupportResetTokenCodec.decode_request(request_bytes)
    now = _aware_utc(now_fn())
    if now < request.created_at or now >= request.expires_at:
        raise OperatorInputError("Die Reset-Anfrage ist noch nicht oder nicht mehr gültig.")

    _write(output, "\nGeprüfte technische Anfrage:")
    _write(output, f"  Anfragen-ID: {request.reset_request_id}")
    _write(output, f"  Installations-ID: {_short_identifier(request.installation_id)}")
    _write(output, f"  Lokale Konto-ID: {_short_identifier(request.user_id)}")
    _write(output, f"  Erstellt: {_display_time(request.created_at)}")
    _write(output, f"  Anfrage gültig bis: {_display_time(request.expires_at)}")
    confirmation = input_fn(
        "Bestätigen Sie mit JA, dass diese Anfrage vom betroffenen Gerät stammt: "
    ).strip()
    if confirmation != "JA":
        _write(output, "Abgebrochen. Es wurde kein Reset-Code erzeugt.")
        return 2

    private_path = _required_path(
        input_fn("Pfad zum verschlüsselten privaten PKCS#8-Schlüssel: "),
        "private Schlüsseldatei",
    )
    public_path = _required_path(
        input_fn("Pfad zur zugehörigen öffentlichen Schlüsselbeschreibung: "),
        "öffentliche Schlüsselbeschreibung",
    )
    _validate_private_key_file(private_path)
    descriptor, expected_public = _load_public_descriptor(public_path)

    private_key = None
    passphrase = b""
    for attempt in range(1, 4):
        entered = getpass_fn(
            f"Passphrase für den privaten Schlüssel (Versuch {attempt}/3): "
        )
        passphrase = entered.encode("utf-8")
        entered = ""
        if not passphrase or len(passphrase) > MAX_PASSPHRASE_BYTES:
            _write(output, "Der private Schlüssel konnte nicht entsperrt werden.")
            continue
        try:
            loaded = serialization.load_pem_private_key(
                private_path.read_bytes(), password=passphrase
            )
        except (OSError, TypeError, ValueError):
            _write(output, "Der private Schlüssel konnte nicht entsperrt werden.")
            continue
        if not isinstance(loaded, Ed25519PrivateKey):
            passphrase = b""
            raise OperatorInputError("Die gewählte Datei ist kein Ed25519-Schlüssel.")
        actual_public = loaded.public_key().public_bytes_raw()
        if actual_public != expected_public:
            passphrase = b""
            raise OperatorInputError(
                "Privater Schlüssel und öffentliche Schlüsselbeschreibung passen nicht zusammen."
            )
        private_key = loaded
        break
    if private_key is None:
        passphrase = b""
        raise OperatorInputError("Der private Schlüssel wurde nach drei Versuchen gesperrt.")
    private_key = None

    minutes = _choose_lifetime(input_fn)
    output_path = _token_output_path(
        input_fn("Zielpfad für die Reset-Code-Datei (.jkmresettoken): ")
    )
    token = generate_token_from_request_bytes(
        request_bytes=request_bytes,
        private_key_path=private_path,
        key_id=str(descriptor["key_id"]),
        passphrase=passphrase,
        now=now,
        lifetime=timedelta(minutes=minutes),
        output_path=output_path,
    )
    passphrase = b""
    payload, _canonical, _signature = SupportResetTokenCodec.decode(token)

    show = input_fn(
        "Reset-Code zusätzlich im Terminal anzeigen? [nein/JA]: "
    ).strip()
    if show == "JA":
        _write(
            output,
            "Warnung: Behandeln Sie den kurz gültigen Code vertraulich und protokollieren Sie ihn nicht.",
        )
        _write(output, token)
    token = ""
    _write(output, "\nReset-Code sicher erstellt.")
    _write(output, f"  Zieldatei: {output_path}")
    _write(output, f"  Gültig bis: {_display_time(payload.expires_at)}")
    _write(output, f"  key_id: {descriptor['key_id']}")
    _write(output, f"  Fingerprint (SHA-256): {descriptor['fingerprint_sha256']}")
    return 0


def _read_request(input_fn: Callable[[str], str], output: TextIO) -> bytes:
    _write(output, "\nReset-Anfrage bereitstellen:")
    _write(output, "  1 = Datei auswählen (Pfad eingeben)")
    _write(output, "  2 = kopierten Anfrageblock einfügen")
    choice = input_fn("Auswahl [1]: ").strip() or "1"
    if choice == "1":
        path = _required_path(input_fn("Pfad zur .jkmresetrequest-Datei: "), "Anfragedatei")
        if path.is_symlink() or not path.is_file():
            raise OperatorInputError("Die Anfragedatei ist nicht sicher lesbar.")
        try:
            with path.open("rb") as stream:
                payload = stream.read(MAX_INPUT_BYTES + 1)
        except OSError as exc:
            raise OperatorInputError("Die Anfragedatei konnte nicht gelesen werden.") from exc
        if len(payload) > MAX_INPUT_BYTES:
            raise OperatorInputError("Die Anfragedatei ist größer als das erlaubte Format.")
        return payload.rstrip(b"\r\n")
    if choice == "2":
        text = input_fn("Anfrageblock vollständig in einer Zeile einfügen: ")
        try:
            payload = text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise OperatorInputError("Der Anfrageblock hat ein ungültiges Format.") from exc
        if not payload or len(payload) > MAX_INPUT_BYTES:
            raise OperatorInputError("Der Anfrageblock hat ein ungültiges Format.")
        return payload
    raise OperatorInputError("Ungültige Auswahl für die Reset-Anfrage.")


def _load_public_descriptor(path: Path) -> tuple[dict[str, object], bytes]:
    if path.is_symlink() or not path.is_file():
        raise OperatorInputError("Die öffentliche Schlüsselbeschreibung ist nicht sicher lesbar.")
    try:
        raw = path.read_bytes()
        if len(raw) > MAX_INPUT_BYTES:
            raise OperatorInputError("Die öffentliche Schlüsselbeschreibung ist zu groß.")
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OperatorInputError("Die öffentliche Schlüsselbeschreibung ist ungültig.") from exc
    if not isinstance(value, dict) or set(value) != PUBLIC_DESCRIPTOR_FIELDS:
        raise OperatorInputError("Die öffentliche Schlüsselbeschreibung ist ungültig.")
    if (
        value["format_version"] != 1
        or value["algorithm"] != "Ed25519"
        or value["intended_status"] != "active"
        or not isinstance(value["key_id"], str)
        or not KEY_ID_PATTERN.fullmatch(value["key_id"])
    ):
        raise OperatorInputError("Der Support-Schlüssel ist nicht für Signaturen aktiv.")
    encoded_public = value["public_key"]
    if not isinstance(encoded_public, str) or len(encoded_public) != 43 or "=" in encoded_public:
        raise OperatorInputError("Die öffentliche Schlüsselbeschreibung ist ungültig.")
    try:
        public = base64.b64decode(
            encoded_public + "=", altchars=b"-_", validate=True
        )
    except (binascii.Error, ValueError, TypeError) as exc:
        raise OperatorInputError("Die öffentliche Schlüsselbeschreibung ist ungültig.") from exc
    fingerprint = hashlib.sha256(public).hexdigest()
    if (
        len(public) != 32
        or not isinstance(value["fingerprint_sha256"], str)
        or not FINGERPRINT_PATTERN.fullmatch(value["fingerprint_sha256"])
        or fingerprint != value["fingerprint_sha256"]
    ):
        raise OperatorInputError("Der öffentliche Schlüssel-Fingerprint ist ungültig.")
    return value, public


def _validate_private_key_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise OperatorInputError("Die private Schlüsseldatei ist nicht sicher lesbar.")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise OperatorInputError("Die private Schlüsseldatei benötigt Dateirechte 600.")
    try:
        prefix = path.read_bytes()[:64]
    except OSError as exc:
        raise OperatorInputError("Die private Schlüsseldatei konnte nicht gelesen werden.") from exc
    if b"BEGIN ENCRYPTED PRIVATE KEY" not in prefix:
        raise OperatorInputError("Nur verschlüsselte PKCS#8-Schlüssel werden akzeptiert.")


def _choose_lifetime(input_fn: Callable[[str], str]) -> int:
    raw = input_fn("Gültigkeitsdauer 15, 30, 60 oder 120 Minuten [30]: ").strip()
    if not raw:
        return 30
    try:
        minutes = int(raw)
    except ValueError as exc:
        raise OperatorInputError("Ungültige Gültigkeitsdauer.") from exc
    if minutes not in ALLOWED_LIFETIMES:
        raise OperatorInputError("Zulässig sind nur 15, 30, 60 oder 120 Minuten.")
    return minutes


def _token_output_path(raw: str) -> Path:
    if not raw.strip():
        raise OperatorInputError("Ohne bewussten Zielpfad wird keine Datei geschrieben.")
    path = Path(raw.strip()).expanduser()
    if path.suffix != ".jkmresettoken":
        path = path.with_suffix(".jkmresettoken")
    if path.exists() or path.is_symlink():
        raise OperatorInputError("Die Zieldatei existiert bereits und wird nicht überschrieben.")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise OperatorInputError("Der Zielordner ist nicht sicher verfügbar.")
    return path.resolve(strict=False)


def _required_path(raw: str, label: str) -> Path:
    if not raw.strip():
        raise OperatorInputError(f"Es wurde keine {label} gewählt.")
    path = Path(raw.strip()).expanduser()
    return path if path.is_absolute() else Path.cwd() / path


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise OperatorInputError("Die Systemzeit ist nicht eindeutig verfügbar.")
    return value.astimezone(UTC)


def _display_time(value: datetime) -> str:
    return value.astimezone().strftime("%d.%m.%Y, %H:%M:%S %Z")


def _short_identifier(value: str) -> str:
    return f"{value[:8]}…{value[-4:]}"


def _write(stream: TextIO, text: str) -> None:
    print(text, file=stream, flush=True)


def main() -> int:
    if len(sys.argv) != 1:
        print("Dieses Werkzeug übernimmt keine Passphrasen oder Secrets als Argumente.", file=sys.stderr)
        return 2
    try:
        return run_interactive()
    except (OperatorInputError, ValueError) as exc:
        print(f"Sicherer Abbruch: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nAbgebrochen. Es wurde kein weiterer Schritt ausgeführt.", file=sys.stderr)
        return 130
    except Exception:
        print("Sicherer Abbruch: Der Reset-Code konnte nicht erzeugt werden.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
