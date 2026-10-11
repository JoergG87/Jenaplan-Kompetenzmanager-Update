#!/usr/bin/env python3
"""Resumable, fail-closed automation for the macOS pilot release channel."""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
from typing import Any, Iterable, Mapping, Sequence
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "release" / "release_config.toml"
STATE_POINTER = ROOT / "release" / "release_state.json"
SPARKLE_NAMESPACE = "http://www.andymatuschak.org/xml-namespaces/sparkle"
ET.register_namespace("sparkle", SPARKLE_NAMESPACE)

PHASES = (
    "inspected",
    "prepared",
    "built",
    "package_verified",
    "github_draft_created",
    "github_assets_verified",
    "github_published",
    "appcast_prepared",
    "appcast_published",
    "remote_verified",
)
PUBLISH_PHASES = frozenset(
    {
        "github_draft_created",
        "github_assets_verified",
        "github_published",
        "appcast_prepared",
        "appcast_published",
        "remote_verified",
    }
)
FORBIDDEN_SUFFIXES = {
    ".db",
    ".jkmbackup",
    ".jkmebackup",
    ".jkmedoc",
    ".key",
    ".p12",
    ".pem",
    ".sqlite",
    ".xls",
    ".xlsm",
    ".xlsx",
}
SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization:\s*(?:bearer|token)\s+)\S+"),
    re.compile(r"(?i)(?:token|password|passphrase|private[_ -]?key)\s*[=:]\s*\S+"),
    re.compile(r"https://[^/\s:@]+:[^@\s/]+@"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
)
PRIVATE_PATH_PATTERNS = ("/Users/", "/private/tmp/", "/var/folders/")


class ReleaseError(RuntimeError):
    """A safety or consistency gate blocked the release."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def redact(text: str) -> str:
    result = text
    for pattern in SECRET_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def sanitize_public(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: sanitize_public(item)
            for key, item in value.items()
            if key
            not in {
                "build_directory",
                "output_directory",
                "worktree_path",
                "local_manifest_path",
            }
        }
    if isinstance(value, list):
        return [sanitize_public(item) for item in value]
    if isinstance(value, str):
        sanitized = redact(value)
        if any(marker in sanitized for marker in PRIVATE_PATH_PATTERNS):
            return "<local-path-redacted>"
        return sanitized
    return value


def atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.chmod(stat.S_IRUSR | stat.S_IWUSR)
    temporary.replace(path)


class Runner:
    """Subprocess boundary with sanitized failures and injectable behavior."""

    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        mutating: bool = False,
        timeout: int = 300,
    ) -> subprocess.CompletedProcess[str]:
        if self.dry_run and mutating:
            return subprocess.CompletedProcess(command, 0, "", "")
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            env=dict(env) if env is not None else None,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if completed.returncode:
            detail = redact((completed.stderr or completed.stdout).strip())
            raise ReleaseError(
                f"Befehl fehlgeschlagen ({Path(command[0]).name}, "
                f"Exit {completed.returncode}): {detail or 'keine Ausgabe'}"
            )
        return completed


@dataclass(frozen=True)
class ReleaseConfig:
    path: Path
    values: Mapping[str, Any]

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG) -> "ReleaseConfig":
        with path.open("rb") as source:
            values = tomllib.load(source)
        required = {
            "schema_version",
            "product_name",
            "bundle_id",
            "minimum_macos",
            "architecture",
            "source_branch",
            "github_repository",
            "pilot_appcast_repository",
            "pilot_appcast_branch",
            "pilot_appcast_path",
            "pilot_feed_url",
            "pilot_pages_prefix",
            "stable_enabled",
            "sparkle_public_key_file",
            "sparkle_keychain_account",
            "sparkle_root_environment",
            "build_script",
            "build_requirements",
            "release_notes_source",
            "output_root",
            "restore_smoke_required",
            "asset_patterns",
            "documentation_sources",
            "package_gates",
            "reference_release",
        }
        missing = sorted(required - values.keys())
        if missing:
            raise ReleaseError(f"Releasekonfiguration unvollständig: {', '.join(missing)}")
        if values["schema_version"] != 1:
            raise ReleaseError("Unbekannte Releasekonfigurationsversion.")
        if values["stable_enabled"] is not False:
            raise ReleaseError("Stable muss in der Pilotkonfiguration deaktiviert bleiben.")
        for name in ("pilot_feed_url", "pilot_pages_prefix"):
            value = str(values[name])
            if not value.startswith("https://") or any(
                marker in value for marker in ("@", "localhost", "/Users/", "/private/")
            ):
                raise ReleaseError(f"{name} muss eine öffentliche feste HTTPS-URL sein.")
        repository_pattern = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
        for name in ("github_repository", "pilot_appcast_repository"):
            if not repository_pattern.fullmatch(str(values[name])):
                raise ReleaseError(f"Ungültiges GitHub-Repository in {name}.")
        for relative in (
            values["sparkle_public_key_file"],
            values["build_script"],
            values["build_requirements"],
            values["release_notes_source"],
            *values["documentation_sources"],
        ):
            candidate = ROOT / str(relative)
            if not candidate.is_file():
                raise ReleaseError(f"Konfigurierte Quelldatei fehlt: {relative}")
        if not values["asset_patterns"] or not values["package_gates"]:
            raise ReleaseError("Assetmuster und Paketgates dürfen nicht leer sein.")
        return cls(path=path, values=values)

    def __getitem__(self, key: str) -> Any:
        return self.values[key]

    @property
    def output_root(self) -> Path:
        return ROOT / str(self["output_root"])


def git(runner: Runner, *args: str, cwd: Path = ROOT, mutating: bool = False) -> str:
    return runner.run(
        ["git", *args], cwd=cwd, mutating=mutating, timeout=600
    ).stdout.strip()


def current_version() -> tuple[str, int]:
    namespace: dict[str, Any] = {}
    exec((ROOT / "src" / "version.py").read_text(encoding="utf-8"), namespace)
    return str(namespace["APP_VERSION"]), int(namespace["APP_BUILD_VERSION"])


def parse_remote_repository(remote: str) -> str:
    match = re.search(
        r"(?:github\.com[:/])(?P<repo>[^/\s]+/[^/\s]+?)(?:\.git)?$", remote
    )
    if not match:
        raise ReleaseError("Git-Remote ist kein erkennbares GitHub-Repository.")
    return match.group("repo")


def fetch_bytes(url: str, *, timeout: int = 60) -> bytes:
    completed = subprocess.run(
        [
            "/usr/bin/curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--proto",
            "=https",
            "--tlsv1.2",
            "--max-time",
            str(timeout),
            "--user-agent",
            "Jenaplan-Release-Automation/1",
            url,
        ],
        check=False,
        capture_output=True,
    )
    if completed.returncode:
        detail = redact(completed.stderr.decode("utf-8", errors="replace").strip())
        raise ReleaseError(
            f"Öffentlicher HTTPS-Abruf fehlgeschlagen: {detail or completed.returncode}"
        )
    return completed.stdout


def parse_appcast(payload: bytes) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise ReleaseError(f"Pilot-Appcast ist nicht wohlgeformt: {error}") from error
    items: list[dict[str, Any]] = []
    for item in root.findall("./channel/item"):
        enclosure = item.find("enclosure")
        version = item.find(f"{{{SPARKLE_NAMESPACE}}}version")
        short_version = item.find(f"{{{SPARKLE_NAMESPACE}}}shortVersionString")
        minimum = item.find(f"{{{SPARKLE_NAMESPACE}}}minimumSystemVersion")
        hardware = item.find(f"{{{SPARKLE_NAMESPACE}}}hardwareRequirements")
        notes = item.find(f"{{{SPARKLE_NAMESPACE}}}releaseNotesLink")
        if enclosure is None or version is None or short_version is None:
            raise ReleaseError("Pilot-Appcast enthält einen unvollständigen Eintrag.")
        try:
            build = int(version.text or "")
            length = int(enclosure.get("length", ""))
        except ValueError as error:
            raise ReleaseError("Pilot-Appcast enthält ungültige Zahlenwerte.") from error
        items.append(
            {
                "build": build,
                "version": short_version.text or "",
                "minimum_macos": minimum.text if minimum is not None else "",
                "architecture": hardware.text if hardware is not None else "",
                "url": enclosure.get("url", ""),
                "length": length,
                "signature": enclosure.get(f"{{{SPARKLE_NAMESPACE}}}edSignature", ""),
                "release_notes_url": notes.text if notes is not None else "",
                "release_notes_signature": (
                    notes.get(f"{{{SPARKLE_NAMESPACE}}}edSignature", "")
                    if notes is not None
                    else ""
                ),
                "release_notes_length": (
                    int(notes.get(f"{{{SPARKLE_NAMESPACE}}}length", "0"))
                    if notes is not None
                    else 0
                ),
            }
        )
    if not items:
        raise ReleaseError("Pilot-Appcast enthält keinen Releaseeintrag.")
    return items


def latest_pilot_build(items: Iterable[Mapping[str, Any]]) -> int:
    return max(int(item["build"]) for item in items)


def release_tag(version: str, build: int) -> str:
    return f"v{version}-build{build}"


def expected_asset_names(config: ReleaseConfig, version: str, build: int) -> list[str]:
    return [
        str(pattern).format(version=version, build=build)
        for pattern in config["asset_patterns"]
    ]


class Manifest:
    def __init__(self, local_path: Path, public_path: Path, data: dict[str, Any]) -> None:
        self.local_path = local_path
        self.public_path = public_path
        self.data = data

    @classmethod
    def create(
        cls,
        *,
        config: ReleaseConfig,
        version: str,
        build: int,
        source_commit: str,
        branch: str,
    ) -> "Manifest":
        run_root = config.output_root / (
            f"{version}-build{build}-{source_commit[:12]}"
        )
        local_path = run_root / "release-manifest.local.json"
        public_path = run_root / "release-manifest.json"
        data: dict[str, Any] = {
            "manifest_schema_version": 1,
            "version": version,
            "build": build,
            "source_commit": source_commit,
            "branch": branch,
            "created_at": utc_now(),
            "host_system": platform.platform(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "pyinstaller_version": None,
            "pyside_version": None,
            "sparkle_version": None,
            "worktree_path": None,
            "build_directory": None,
            "output_directory": str(run_root),
            "assets": [],
            "package_gates": {},
            "restore_smoke_status": "not_requested",
            "github_release_id": None,
            "github_release_url": None,
            "tag": release_tag(version, build),
            "pilot_appcast_commit": None,
            "published_feed_url": None,
            "phase_status": {phase: "pending" for phase in PHASES},
            "current_phase": None,
            "error": None,
        }
        manifest = cls(local_path, public_path, data)
        manifest.save()
        return manifest

    @classmethod
    def load(cls, path: Path) -> "Manifest":
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("manifest_schema_version") != 1:
            raise ReleaseError("Unbekanntes Manifestformat.")
        public_path = path.with_name("release-manifest.json")
        return cls(path, public_path, data)

    def save(self) -> None:
        atomic_json_write(self.local_path, self.data)
        atomic_json_write(self.public_path, sanitize_public(self.data))
        atomic_json_write(
            STATE_POINTER,
            {
                "schema_version": 1,
                "manifest": str(self.local_path),
                "updated_at": utc_now(),
            },
        )

    def complete(self, phase: str, **updates: Any) -> None:
        if phase not in PHASES:
            raise ReleaseError(f"Unbekannte Phase: {phase}")
        index = PHASES.index(phase)
        incomplete = [
            predecessor
            for predecessor in PHASES[:index]
            if self.data["phase_status"].get(predecessor) != "completed"
        ]
        if incomplete:
            raise ReleaseError(
                f"Phase {phase} vor Vorgängerphase {incomplete[0]} nicht zulässig."
            )
        self.data.update(updates)
        self.data["phase_status"][phase] = "completed"
        self.data["current_phase"] = phase
        self.data["error"] = None
        self.save()

    def fail(self, phase: str, error: Exception) -> None:
        self.data["phase_status"][phase] = "failed"
        self.data["current_phase"] = "failed"
        self.data["error"] = redact(str(error))
        self.save()

    def require(self, phase: str) -> None:
        if self.data["phase_status"].get(phase) != "completed":
            raise ReleaseError(f"Vorausgesetzte Phase fehlt: {phase}")

    def is_complete(self, phase: str) -> bool:
        return self.data["phase_status"].get(phase) == "completed"


def load_active_manifest(path: Path | None = None) -> Manifest:
    if path is None:
        if not STATE_POINTER.is_file():
            raise ReleaseError("Kein vorbereiteter Releaselauf vorhanden.")
        pointer = json.loads(STATE_POINTER.read_text(encoding="utf-8"))
        path = Path(pointer["manifest"])
    if not path.is_file():
        raise ReleaseError("Lokales Releasemanifest fehlt.")
    return Manifest.load(path)


class ReleasePilot:
    def __init__(self, config: ReleaseConfig, runner: Runner | None = None) -> None:
        self.config = config
        self.runner = runner or Runner()

    def _gh_json(self, command: Sequence[str]) -> Any:
        output = self.runner.run(["gh", *command], cwd=ROOT, timeout=120).stdout
        return json.loads(output)

    def _gh_optional_json(self, command: Sequence[str]) -> Any | None:
        try:
            return self._gh_json(command)
        except ReleaseError as error:
            if re.search(
                r"(?:HTTP\s+404|release\s+not\s+found|not\s+found)",
                str(error),
                flags=re.IGNORECASE,
            ):
                return None
            raise

    def _remote_appcast(self) -> list[dict[str, Any]]:
        return parse_appcast(fetch_bytes(str(self.config["pilot_feed_url"])))

    def inspect(
        self,
        *,
        allow_existing: bool = True,
        check_network: bool = True,
    ) -> dict[str, Any]:
        if git(self.runner, "rev-parse", "--is-inside-work-tree") != "true":
            raise ReleaseError("Kein Git-Repository erkannt.")
        branch = git(self.runner, "branch", "--show-current")
        head = git(self.runner, "rev-parse", "HEAD")
        dirty = git(self.runner, "status", "--porcelain=v1", "--untracked-files=all")
        if dirty:
            raise ReleaseError("Index oder Worktree ist nicht sauber.")
        if branch != self.config["source_branch"]:
            raise ReleaseError(
                f"Unerwarteter Branch: {branch}; erwartet {self.config['source_branch']}."
            )
        remote = git(self.runner, "remote", "get-url", "origin")
        if parse_remote_repository(remote) != self.config["github_repository"]:
            raise ReleaseError("Git-Remote weicht von der Releasekonfiguration ab.")
        version, build = current_version()
        report: dict[str, Any] = {
            "status": "ok",
            "branch": branch,
            "head": head,
            "version": version,
            "build": build,
            "working_tree": "clean",
            "stable_enabled": False,
            "network_checked": check_network,
            "sparkle_signer": "not_checked",
        }
        sparkle_root = os.environ.get(
            str(self.config["sparkle_root_environment"]), ""
        ).strip()
        if sparkle_root:
            signer = Path(sparkle_root) / "bin" / "sign_update"
            if not signer.is_file() or not os.access(signer, os.X_OK):
                raise ReleaseError("Konfigurierter Sparkle-Signierweg ist unvollständig.")
            report["sparkle_signer"] = "available"
        else:
            report["sparkle_signer"] = "publication_blocker"
        if not check_network:
            return report
        self.runner.run(["gh", "--version"], timeout=30)
        self.runner.run(["gh", "auth", "status"], timeout=60)
        self.runner.run(
            [
                "gh",
                "repo",
                "view",
                str(self.config["pilot_appcast_repository"]),
                "--json",
                "nameWithOwner",
            ],
            timeout=60,
        )
        tag = release_tag(version, build)
        release_exists = self._remote_release(tag) is not None
        tag_exists = (
            self._gh_optional_json(
                [
                    "api",
                    f"repos/{self.config['github_repository']}/git/ref/tags/{tag}",
                ]
            )
            is not None
        )
        appcast = self._remote_appcast()
        stable = self._gh_optional_json(
            [
                "api",
                f"repos/{self.config['pilot_appcast_repository']}/contents/stable",
                "-H",
                "Accept: application/vnd.github+json",
            ]
        )
        if stable is not None:
            raise ReleaseError("Stable-Verzeichnis ist öffentlich vorhanden.")
        current_pilot = latest_pilot_build(appcast)
        report.update(
            {
                "release_exists": release_exists,
                "tag_exists": tag_exists,
                "tag": tag,
                "pilot_build": current_pilot,
                "already_published": (
                    release_exists or tag_exists or build <= current_pilot
                ),
            }
        )
        if not allow_existing and report["already_published"]:
            raise ReleaseError(
                f"Build {build} ist bereits veröffentlicht oder nicht neuer "
                f"als Pilotbuild {current_pilot}."
            )
        return report

    def prepare(
        self,
        *,
        version: str | None,
        build: int | None,
        check_network: bool = True,
    ) -> Manifest:
        inspection = self.inspect(allow_existing=False, check_network=check_network)
        source_version, source_build = current_version()
        version = version or source_version
        build = build or source_build
        if (version, build) != (source_version, source_build):
            raise ReleaseError(
                "Version und Build müssen vor Prepare separat in src.version "
                "committed sein."
            )
        if not re.fullmatch(r"\d+\.\d+\.\d+", version) or build <= 0:
            raise ReleaseError("Ungültige Version oder Buildnummer.")
        manifest = Manifest.create(
            config=self.config,
            version=version,
            build=build,
            source_commit=inspection["head"],
            branch=inspection["branch"],
        )
        manifest.complete("inspected")
        manifest.complete("prepared")
        return manifest

    def _ensure_manifest_source(self, manifest: Manifest) -> None:
        if git(self.runner, "cat-file", "-t", manifest.data["source_commit"]) != "commit":
            raise ReleaseError("Manifest-Commit ist lokal nicht vorhanden.")
        version_payload = git(
            self.runner,
            "show",
            f"{manifest.data['source_commit']}:src/version.py",
        )
        version_match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', version_payload)
        build_match = re.search(
            r'APP_BUILD_VERSION\s*=\s*"(\d+)"', version_payload
        )
        if not version_match or not build_match:
            raise ReleaseError("Versionsquelle im Manifest-Commit ist ungültig.")
        if (
            version_match.group(1) != manifest.data["version"]
            or int(build_match.group(1)) != manifest.data["build"]
        ):
            raise ReleaseError("Manifest und Commit-Versionsquelle weichen ab.")

    def _collect_versions(self, venv_python: Path) -> dict[str, str]:
        command = [
            str(venv_python),
            "-c",
            (
                "from importlib.metadata import version;"
                "print(version('pyinstaller'));"
                "print(version('PySide6'))"
            ),
        ]
        values = self.runner.run(command, timeout=60).stdout.splitlines()
        if len(values) != 2:
            raise ReleaseError("Buildlaufzeiten konnten nicht bestimmt werden.")
        return {"pyinstaller_version": values[0], "pyside_version": values[1]}

    def build(self, manifest: Manifest) -> None:
        manifest.require("prepared")
        if manifest.is_complete("built"):
            return
        self._ensure_manifest_source(manifest)
        run_root = manifest.local_path.parent
        worktree_parent = Path(
            tempfile.mkdtemp(
                prefix=(
                    f"jkm-release-{manifest.data['version']}-"
                    f"{manifest.data['build']}-"
                )
            )
        )
        worktree_parent.chmod(0o700)
        workspace = worktree_parent / "source"
        build_root = workspace / "build" / "macos-pilot"
        dist_root = workspace / "dist" / "macos"
        artifacts_root = run_root / "artifacts"
        if artifacts_root.exists():
            raise ReleaseError("Buildziel existiert bereits: artifacts")
        try:
            git(
                self.runner,
                "worktree",
                "add",
                "--detach",
                str(workspace),
                manifest.data["source_commit"],
                mutating=True,
            )
            environment = os.environ.copy()
            environment.update(
                {
                    "JENAPLAN_MACOS_BUILD_ROOT": str(build_root),
                    "JENAPLAN_MACOS_DIST_ROOT": str(dist_root),
                }
            )
            self.runner.run(
                [
                    str(workspace / self.config["build_script"]),
                    "--data-mode",
                    "release",
                    "--defer-package-tests",
                ],
                cwd=workspace,
                env=environment,
                mutating=True,
                timeout=7200,
            )
            artifacts_root.mkdir(mode=0o700)
            version = manifest.data["version"]
            build = manifest.data["build"]
            dmg_name = expected_asset_names(self.config, version, build)[0]
            dmg_source = dist_root / dmg_name
            if not dmg_source.is_file():
                raise ReleaseError("Erwartetes DMG wurde nicht erzeugt.")
            shutil.copy2(dmg_source, artifacts_root / dmg_name)
            documentation_name = expected_asset_names(self.config, version, build)[1]
            with zipfile.ZipFile(
                artifacts_root / documentation_name,
                "w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                for source_name in self.config["documentation_sources"]:
                    source = workspace / source_name
                    archive.write(source, arcname=Path(source_name).name)
                for pdf in sorted(dist_root.glob("*.pdf")):
                    archive.write(pdf, arcname=pdf.name)
            release_notes = artifacts_root / "GITHUB_RELEASE_NOTES.md"
            release_notes.write_text(
                (workspace / self.config["release_notes_source"]).read_text(encoding="utf-8")
                .replace("{{PILOT_VERSION}}", str(version))
                .replace("{{PILOT_BUILD}}", str(build)),
                encoding="utf-8",
            )
            asset_paths = [
                artifacts_root / dmg_name,
                artifacts_root / documentation_name,
            ]
            checksums_name = expected_asset_names(self.config, version, build)[2]
            inventory_name = expected_asset_names(self.config, version, build)[3]
            checksums = artifacts_root / checksums_name
            checksums.write_text(
                "".join(
                    f"{sha256_file(path)}  {path.name}\n" for path in asset_paths
                ),
                encoding="utf-8",
            )
            inventory = artifacts_root / inventory_name
            inventory.write_text(
                "\n".join(
                    [
                        f"Version: {version}",
                        f"Build: {build}",
                        f"Quellcommit: {manifest.data['source_commit']}",
                        f"Architektur: {self.config['architecture']}",
                        f"Bundle-ID: {self.config['bundle_id']}",
                        f"Mindest-macOS: {self.config['minimum_macos']}",
                        "Kanal: pilot",
                        "Stable: deaktiviert",
                        "",
                        "Artefakte:",
                        *[
                            f"{path.stat().st_size}  {sha256_file(path)}  {path.name}"
                            for path in asset_paths
                        ],
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            asset_paths.extend([checksums, inventory])
            versions = self._collect_versions(build_root / "venv" / "bin" / "python")
            sparkle_version = self._sparkle_version(build_root / "sparkle")
            manifest.complete(
                "built",
                worktree_path=str(workspace),
                build_directory=str(build_root),
                output_directory=str(run_root),
                assets=[
                    {
                        "name": path.name,
                        "size": path.stat().st_size,
                        "sha256": sha256_file(path),
                        "local_path": str(path),
                    }
                    for path in asset_paths
                ],
                sparkle_version=sparkle_version,
                **versions,
            )
        except Exception as error:
            manifest.fail("built", error)
            raise

    @staticmethod
    def _sparkle_version(sparkle_root: Path) -> str:
        candidates = tuple(
            sparkle_root.glob("**/Sparkle.framework/**/Resources/Info.plist")
        )

        versions = set()

        for candidate in candidates:
            try:
                with candidate.open("rb") as source:
                    info = plistlib.load(source)
            except Exception:
                continue

            version = (
                info.get("CFBundleShortVersionString")
                or info.get("CFBundleVersion")
            )

            if version:
                versions.add(str(version))

        if not versions:
            raise ReleaseError("Keine Sparkle-Version im Buildroot gefunden.")

        if len(versions) > 1:
            raise ReleaseError(
                f"Mehrere unterschiedliche Sparkle-Versionen gefunden: {sorted(versions)}"
            )

        return next(iter(versions))

    def _asset_path(self, manifest: Manifest, name: str) -> Path:
        matches = [
            Path(asset["local_path"])
            for asset in manifest.data["assets"]
            if asset["name"] == name
        ]
        if len(matches) != 1 or not matches[0].is_file():
            raise ReleaseError(f"Manifest-Asset fehlt: {name}")
        asset = next(
            item for item in manifest.data["assets"] if item["name"] == name
        )
        if (
            matches[0].stat().st_size != asset["size"]
            or sha256_file(matches[0]) != asset["sha256"]
        ):
            raise ReleaseError(f"Manifest-Asset wurde verändert: {name}")
        return matches[0]

    def _scan_forbidden(self, root: Path) -> None:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES:
                raise ReleaseError(f"Verbotenes Paketartefakt: {path.name}")
            if path.is_file() and path.suffix.lower() in {".json", ".md", ".plist", ".txt"}:
                payload = path.read_bytes()
                if any(marker.encode() in payload for marker in PRIVATE_PATH_PATTERNS):
                    raise ReleaseError(f"Privater Entwicklerpfad im Paket: {path.name}")
                lowered = payload.lower()
                if any(
                    marker in lowered
                    for marker in (
                        b"begin private key",
                        b"github_token",
                        b"ghp_",
                    )
                ):
                    raise ReleaseError(f"Mögliches Secret im Paket: {path.name}")

    def package_test(self, manifest: Manifest, *, restore_smoke: bool) -> None:
        manifest.require("built")
        if manifest.is_complete("package_verified"):
            return
        version = manifest.data["version"]
        build = manifest.data["build"]
        dmg = self._asset_path(
            manifest, expected_asset_names(self.config, version, build)[0]
        )
        mount_root = Path(tempfile.mkdtemp(prefix="jkm-release-mount-"))
        gates = {name: "pending" for name in self.config["package_gates"]}
        try:
            self.runner.run(["hdiutil", "verify", str(dmg)], timeout=600)
            gates["hdiutil_verify"] = "passed"
            attach = self.runner.run(
                [
                    "hdiutil",
                    "attach",
                    str(dmg),
                    "-readonly",
                    "-nobrowse",
                    "-mountpoint",
                    str(mount_root),
                ],
                mutating=True,
                timeout=300,
            )
            del attach
            app = mount_root / f"{self.config['product_name']}.app"
            build_python = (
                Path(manifest.data["build_directory"]) / "venv" / "bin" / "python"
            )
            self.runner.run(
                [
                    str(build_python),
                    str(Path(manifest.data["worktree_path"]) / "scripts" / "audit_macos_app_bundle.py"),
                    str(app),
                    "--expected-version",
                    version,
                    "--expected-build",
                    str(build),
                ],
                timeout=900,
            )
            for gate in (
                "bundle_metadata",
                "arm64_only",
                "native_libraries",
                "forbidden_artifacts",
                "developer_paths",
            ):
                gates[gate] = "passed"
            self.runner.run(
                ["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)],
                timeout=300,
            )
            gates["codesign_deep_strict"] = "passed"
            with (app / "Contents" / "Info.plist").open("rb") as source:
                info = plistlib.load(source)
            if info.get("SUFeedURL") != self.config["pilot_feed_url"]:
                raise ReleaseError("Pilotfeed im Bundle ist inkonsistent.")
            if any("stable" in str(value).lower() for value in info.values()):
                raise ReleaseError("Stable-Feed ist im Bundle aktiviert.")
            gates["pilot_feed"] = "passed"
            gates["stable_disabled"] = "passed"
            sparkle_info = (
                app
                / "Contents"
                / "Frameworks"
                / "Sparkle.framework"
                / "Versions"
                / "B"
                / "Resources"
                / "Info.plist"
            )
            with sparkle_info.open("rb") as source:
                bundled_sparkle = plistlib.load(source)
            bundled_version = str(
                bundled_sparkle.get("CFBundleShortVersionString")
                or bundled_sparkle.get("CFBundleVersion")
            )
            if bundled_version != manifest.data["sparkle_version"]:
                raise ReleaseError("Sparkle-Version weicht vom Buildmanifest ab.")
            gates["sparkle_version"] = "passed"
            self.runner.run(
                [
                    str(build_python),
                    str(Path(manifest.data["worktree_path"]) / "scripts" / "smoke_test_macos_app.py"),
                    str(app),
                    "--expected-data-mode",
                    "release",
                ],
                timeout=900,
            )
            gates["app_start_smoke"] = "passed"
            self._scan_forbidden(mount_root)
            restore_status = "not_requested"
            if restore_smoke:
                self.runner.run(
                    [
                        str(build_python),
                        str(
                            Path(manifest.data["worktree_path"])
                            / "scripts"
                            / "smoke_test_packaged_restore_worker.py"
                        ),
                        str(app),
                    ],
                    timeout=1200,
                )
                restore_status = "passed"
            if self.config["restore_smoke_required"] and restore_status != "passed":
                raise ReleaseError("Das Releaseprofil verlangt einen Restore-Smoke.")
            if set(gates.values()) != {"passed"}:
                raise ReleaseError("Nicht alle Paketgates wurden erfolgreich abgeschlossen.")
            manifest.complete(
                "package_verified",
                package_gates=gates,
                restore_smoke_status=restore_status,
            )
        except Exception as error:
            manifest.data["package_gates"] = gates
            manifest.fail("package_verified", error)
            raise
        finally:
            self.runner.run(
                ["hdiutil", "detach", str(mount_root), "-quiet"],
                mutating=True,
                timeout=120,
            ) if mount_root.exists() and any(mount_root.iterdir()) else None
            shutil.rmtree(mount_root, ignore_errors=True)

    def _remote_release(self, tag: str) -> dict[str, Any] | None:
        return self._gh_optional_json(
            [
                "release",
                "view",
                tag,
                "--repo",
                str(self.config["github_repository"]),
                "--json",
                (
                    "databaseId,tagName,name,isDraft,isPrerelease,"
                    "publishedAt,targetCommitish,url,assets"
                ),
            ]
        )

    def _manifest_assets_by_name(
        self, manifest: Manifest
    ) -> dict[str, Mapping[str, Any]]:
        result = {asset["name"]: asset for asset in manifest.data["assets"]}
        expected = set(
            expected_asset_names(
                self.config, manifest.data["version"], manifest.data["build"]
            )
        )
        if set(result) != expected:
            raise ReleaseError("Manifest enthält nicht exakt die freigegebenen Assets.")
        for asset in result.values():
            self._asset_path(manifest, str(asset["name"]))
        return result

    def _verify_remote_assets(
        self, manifest: Manifest, release: Mapping[str, Any]
    ) -> None:
        local = self._manifest_assets_by_name(manifest)
        remote = {asset["name"]: asset for asset in release.get("assets", [])}
        if set(local) != set(remote):
            raise ReleaseError("GitHub-Assets weichen von der Manifest-Allowlist ab.")
        download_root = Path(tempfile.mkdtemp(prefix="jkm-release-assets-"))
        try:
            for name, expected in local.items():
                metadata = remote[name]
                if int(metadata["size"]) != int(expected["size"]):
                    raise ReleaseError(f"GitHub-Assetgröße weicht ab: {name}")
                target = download_root / name
                self.runner.run(
                    [
                        "gh",
                        "release",
                        "download",
                        str(manifest.data["tag"]),
                        "--repo",
                        str(self.config["github_repository"]),
                        "--pattern",
                        name,
                        "--dir",
                        str(download_root),
                    ],
                    mutating=True,
                    timeout=900,
                )
                if sha256_file(target) != expected["sha256"]:
                    raise ReleaseError(f"GitHub-Asset-Hash weicht ab: {name}")
        finally:
            shutil.rmtree(download_root, ignore_errors=True)

    def _resolve_remote_tag_commit(self, tag: str) -> str:
        repository = str(self.config["github_repository"])
        reference = self._gh_json(
            ["api", f"repos/{repository}/git/ref/tags/{tag}"]
        )
        target = reference["object"]
        if target["type"] == "commit":
            return str(target["sha"])
        if target["type"] != "tag":
            raise ReleaseError("GitHub-Tag besitzt einen unbekannten Zieltyp.")
        tag_object = self._gh_json(
            ["api", f"repos/{repository}/git/tags/{target['sha']}"]
        )
        if tag_object["object"]["type"] != "commit":
            raise ReleaseError("Annotierter Tag zeigt nicht direkt auf einen Commit.")
        return str(tag_object["object"]["sha"])

    def publish_github(self, manifest: Manifest) -> None:
        manifest.require("package_verified")
        assets = self._manifest_assets_by_name(manifest)
        tag = str(manifest.data["tag"])
        commit = str(manifest.data["source_commit"])
        self.runner.run(["gh", "auth", "status"], timeout=60)
        existing = self._remote_release(tag)
        if existing is not None:
            if self._resolve_remote_tag_commit(tag) != commit:
                raise ReleaseError("Vorhandener Release-Tag zeigt auf einen anderen Commit.")
            self._verify_remote_assets(manifest, existing)
            if existing["isDraft"]:
                manifest.complete(
                    "github_draft_created",
                    github_release_id=existing["databaseId"],
                    github_release_url=existing["url"],
                )
                manifest.complete("github_assets_verified")
                self.runner.run(
                    [
                        "gh",
                        "release",
                        "edit",
                        tag,
                        "--repo",
                        str(self.config["github_repository"]),
                        "--draft=false",
                        "--prerelease",
                        "--latest=false",
                    ],
                    mutating=True,
                    timeout=120,
                )
            elif not existing["isPrerelease"]:
                raise ReleaseError("Vorhandener Release ist kein Pre-Release.")
            if not manifest.is_complete("github_draft_created"):
                manifest.complete(
                    "github_draft_created",
                    github_release_id=existing["databaseId"],
                    github_release_url=existing["url"],
                )
            if not manifest.is_complete("github_assets_verified"):
                manifest.complete("github_assets_verified")
            manifest.complete("github_published")
            return

        git(
            self.runner,
            "push",
            "origin",
            f"{commit}:refs/heads/{manifest.data['branch']}",
            mutating=True,
        )
        local_tag = git(self.runner, "tag", "--list", tag)
        if local_tag:
            tagged = git(self.runner, "rev-list", "-n", "1", tag)
            if tagged != commit:
                raise ReleaseError("Lokaler Tag kollidiert mit dem Manifest-Commit.")
        else:
            git(
                self.runner,
                "tag",
                "-a",
                tag,
                commit,
                "-m",
                f"{self.config['product_name']} {manifest.data['version']} "
                f"Build {manifest.data['build']} Pilot",
                mutating=True,
            )
        git(self.runner, "push", "origin", f"refs/tags/{tag}", mutating=True)
        notes = manifest.local_path.parent / "artifacts" / "GITHUB_RELEASE_NOTES.md"
        command = [
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            str(self.config["github_repository"]),
            "--target",
            commit,
            "--title",
            f"{self.config['product_name']} {manifest.data['version']} "
            f"(Build {manifest.data['build']}) – Pilot",
            "--notes-file",
            str(notes),
            "--draft",
            "--prerelease",
            *[str(Path(asset["local_path"])) for asset in assets.values()],
        ]
        self.runner.run(command, mutating=True, timeout=1800)
        draft = self._remote_release(tag)
        if draft is None or not draft["isDraft"] or not draft["isPrerelease"]:
            raise ReleaseError("GitHub-Draft-Pre-Release wurde nicht korrekt erzeugt.")
        manifest.complete(
            "github_draft_created",
            github_release_id=draft["databaseId"],
            github_release_url=draft["url"],
        )
        try:
            self._verify_remote_assets(manifest, draft)
            manifest.complete("github_assets_verified")
            self.runner.run(
                [
                    "gh",
                    "release",
                    "edit",
                    tag,
                    "--repo",
                    str(self.config["github_repository"]),
                    "--draft=false",
                    "--prerelease",
                    "--latest=false",
                ],
                mutating=True,
                timeout=120,
            )
            published = self._remote_release(tag)
            if (
                published is None
                or published["isDraft"]
                or not published["isPrerelease"]
            ):
                raise ReleaseError("GitHub-Pre-Release wurde nicht veröffentlicht.")
            manifest.complete("github_published")
        except Exception as error:
            manifest.fail(
                "github_assets_verified"
                if not manifest.is_complete("github_assets_verified")
                else "github_published",
                error,
            )
            raise

    def _sparkle_signer(self) -> Path:
        sparkle_root = os.environ.get(
            str(self.config["sparkle_root_environment"]), ""
        ).strip()
        if not sparkle_root:
            raise ReleaseError(
                f"{self.config['sparkle_root_environment']} ist nicht gesetzt."
            )
        signer = Path(sparkle_root) / "bin" / "sign_update"
        if not signer.is_file() or not os.access(signer, os.X_OK):
            raise ReleaseError("Sparkle sign_update ist nicht ausführbar.")
        return signer

    def _sign_update(self, path: Path) -> tuple[str, int]:
        # Sparkle treats XML/HTML specially and may modify them in place.
        # Sign the exact bytes as an opaque archive instead.
        with tempfile.TemporaryDirectory(prefix="jkm-sparkle-sign-") as directory:
            payload = Path(directory) / "payload.bin"
            shutil.copyfile(path, payload)
            payload.chmod(0o600)
            expected_hash = sha256_file(payload)
            expected_length = payload.stat().st_size
            output = self.runner.run(
                [str(self._sparkle_signer()), "--account",
                 str(self.config["sparkle_keychain_account"]), str(payload)],
                timeout=120,
            ).stdout
            signature_match = re.search(r'edSignature="([^"]+)"', output)
            length_match = re.search(r'length="(\d+)"', output)
            if not signature_match or not length_match:
                raise ReleaseError("Sparkle-Signaturausgabe ist unvollständig.")
            if (int(length_match.group(1)) != expected_length
                    or sha256_file(payload) != expected_hash
                    or sha256_file(path) != expected_hash):
                raise ReleaseError("Sparkle-Signaturdaten wurden verändert.")
            return signature_match.group(1), expected_length

    @staticmethod
    def _release_notes_html(source: Path, *, version: str, build: int) -> str:
        markdown = (source.read_text(encoding="utf-8")
                    .replace("{{PILOT_VERSION}}", version)
                    .replace("{{PILOT_BUILD}}", str(build)))
        return (
            "<!doctype html>\n<html lang=\"de\"><head><meta charset=\"utf-8\">"
            f"<title>Version {html.escape(version)} Build {build}</title></head>"
            f"<body><pre>{html.escape(markdown)}</pre></body></html>\n"
        )

    def _build_appcast(
        self,
        *,
        existing_payload: bytes,
        version: str,
        build: int,
        dmg_url: str,
        dmg_length: int,
        dmg_signature: str,
        notes_url: str,
        notes_length: int,
        notes_signature: str,
    ) -> bytes:
        try:
            root = ET.fromstring(existing_payload)
        except ET.ParseError as error:
            raise ReleaseError("Bestehender Pilot-Appcast ist ungültig.") from error
        channel = root.find("./channel")
        if channel is None:
            raise ReleaseError("Bestehender Pilot-Appcast besitzt keinen Channel.")
        items = parse_appcast(existing_payload)
        if build <= latest_pilot_build(items):
            raise ReleaseError("Pilot-Appcast enthält bereits gleichen oder höheren Build.")
        item = ET.Element("item")
        ET.SubElement(item, "title").text = version
        ET.SubElement(item, "pubDate").text = datetime.now().astimezone().strftime(
            "%a, %d %b %Y %H:%M:%S %z"
        )
        ET.SubElement(
            item, f"{{{SPARKLE_NAMESPACE}}}minimumUpdateVersion"
        ).text = "201"
        ET.SubElement(item, f"{{{SPARKLE_NAMESPACE}}}version").text = str(build)
        ET.SubElement(
            item, f"{{{SPARKLE_NAMESPACE}}}shortVersionString"
        ).text = version
        ET.SubElement(
            item, f"{{{SPARKLE_NAMESPACE}}}minimumSystemVersion"
        ).text = str(self.config["minimum_macos"])
        ET.SubElement(
            item, f"{{{SPARKLE_NAMESPACE}}}hardwareRequirements"
        ).text = str(self.config["architecture"])
        notes = ET.SubElement(
            item,
            f"{{{SPARKLE_NAMESPACE}}}releaseNotesLink",
            {
                f"{{{SPARKLE_NAMESPACE}}}edSignature": notes_signature,
                f"{{{SPARKLE_NAMESPACE}}}length": str(notes_length),
            },
        )
        notes.text = notes_url
        ET.SubElement(
            item,
            "enclosure",
            {
                "url": dmg_url,
                "length": str(dmg_length),
                "type": "application/octet-stream",
                f"{{{SPARKLE_NAMESPACE}}}edSignature": dmg_signature,
            },
        )
        first_existing = channel.find("item")
        if first_existing is None:
            channel.append(item)
        else:
            channel.insert(list(channel).index(first_existing), item)
        ET.indent(root, space="    ")
        return (
            b'<?xml version="1.0" standalone="yes"?>\n'
            + ET.tostring(root, encoding="utf-8")
            + b"\n"
        )

    def publish_appcast(self, manifest: Manifest) -> None:
        manifest.require("github_published")
        if manifest.is_complete("appcast_published"):
            return
        version = str(manifest.data["version"])
        build = int(manifest.data["build"])
        dmg_name = expected_asset_names(self.config, version, build)[0]
        expected = next(
            asset for asset in manifest.data["assets"] if asset["name"] == dmg_name
        )
        repository = str(self.config["pilot_appcast_repository"])
        tag = str(manifest.data["tag"])
        dmg_url = (
            f"https://github.com/{repository}/releases/download/{tag}/{dmg_name}"
        )
        temporary_root = Path(tempfile.mkdtemp(prefix="jkm-appcast-publish-"))
        temporary_root.chmod(0o700)
        checkout = temporary_root / "update-repository"
        try:
            public_dmg = temporary_root / dmg_name
            public_dmg.write_bytes(fetch_bytes(dmg_url, timeout=600))
            if (
                public_dmg.stat().st_size != expected["size"]
                or sha256_file(public_dmg) != expected["sha256"]
            ):
                raise ReleaseError("Öffentliches DMG weicht vom Manifest ab.")
            dmg_signature, dmg_length = self._sign_update(public_dmg)
            if dmg_length != expected["size"]:
                raise ReleaseError("Sparkle-DMG-Länge weicht vom Manifest ab.")
            self.runner.run(
                [
                    "git",
                    "clone",
                    "--branch",
                    str(self.config["pilot_appcast_branch"]),
                    "--single-branch",
                    f"https://github.com/{repository}.git",
                    str(checkout),
                ],
                mutating=True,
                timeout=600,
            )
            appcast = checkout / str(self.config["pilot_appcast_path"])
            existing = appcast.read_bytes()
            stable_before = {
                path.relative_to(checkout).as_posix(): sha256_file(path)
                for path in (checkout / "stable").rglob("*")
                if path.is_file()
            } if (checkout / "stable").exists() else {}
            notes_name = f"{self.config['product_name']}-{version}-macOS-arm64.html"
            notes_path = appcast.parent / notes_name
            if notes_path.exists():
                raise ReleaseError("Release-Notes-Zieldatei existiert bereits.")
            notes_path.write_text(
                self._release_notes_html(
                    manifest.local_path.parent / "artifacts" / "GITHUB_RELEASE_NOTES.md",
                    version=version,
                    build=build,
                ),
                encoding="utf-8",
            )
            notes_signature, notes_length = self._sign_update(notes_path)
            notes_url = str(self.config["pilot_pages_prefix"]) + notes_name
            unsigned = self._build_appcast(
                existing_payload=existing,
                version=version,
                build=build,
                dmg_url=dmg_url,
                dmg_length=dmg_length,
                dmg_signature=dmg_signature,
                notes_url=notes_url,
                notes_length=notes_length,
                notes_signature=notes_signature,
            )
            appcast.write_bytes(unsigned)
            feed_signature, feed_length = self._sign_update(appcast)
            if feed_length != len(unsigned):
                raise ReleaseError("Sparkle-Feedlänge ist inkonsistent.")
            appcast.write_bytes(
                unsigned
                + (
                    "<!-- sparkle-signatures:\n"
                    f"edSignature: {feed_signature}\n"
                    f"length: {feed_length}\n"
                    "-->\n"
                ).encode("utf-8")
            )
            parse_appcast(appcast.read_bytes())
            stable_after = {
                path.relative_to(checkout).as_posix(): sha256_file(path)
                for path in (checkout / "stable").rglob("*")
                if path.is_file()
            } if (checkout / "stable").exists() else {}
            if stable_after != stable_before:
                raise ReleaseError("Stable-Dateien wurden verändert.")
            status = git(self.runner, "status", "--porcelain=v1", cwd=checkout)
            expected_status = {
                f" M {self.config['pilot_appcast_path']}",
                f"?? {appcast.parent.relative_to(checkout).as_posix()}/{notes_name}",
            }
            if set(status.splitlines()) != expected_status:
                raise ReleaseError("Update-Repository enthält unerwartete Änderungen.")
            git(
                self.runner,
                "add",
                "--",
                str(self.config["pilot_appcast_path"]),
                f"{appcast.parent.relative_to(checkout).as_posix()}/{notes_name}",
                cwd=checkout,
                mutating=True,
            )
            staged = set(
                git(
                    self.runner,
                    "diff",
                    "--cached",
                    "--name-only",
                    cwd=checkout,
                ).splitlines()
            )
            allowed = {
                str(self.config["pilot_appcast_path"]),
                f"{appcast.parent.relative_to(checkout).as_posix()}/{notes_name}",
            }
            if staged != allowed:
                raise ReleaseError("Appcast-Staging weicht von der Allowlist ab.")
            manifest.complete("appcast_prepared")
            git(
                self.runner,
                "commit",
                "-m",
                f"release(pilot): publish {version} build {build}",
                cwd=checkout,
                mutating=True,
            )
            commit = git(self.runner, "rev-parse", "HEAD", cwd=checkout)
            git(
                self.runner,
                "push",
                "origin",
                str(self.config["pilot_appcast_branch"]),
                cwd=checkout,
                mutating=True,
            )
            manifest.complete(
                "appcast_published",
                pilot_appcast_commit=commit,
                published_feed_url=self.config["pilot_feed_url"],
            )
        except Exception as error:
            phase = (
                "appcast_published"
                if manifest.is_complete("appcast_prepared")
                else "appcast_prepared"
            )
            manifest.fail(phase, error)
            raise
        finally:
            shutil.rmtree(temporary_root, ignore_errors=True)

    @staticmethod
    def _verify_ed25519(path: Path, signature: str, public_key: bytes) -> None:
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PublicKey,
            )
        except ImportError as error:
            raise ReleaseError(
                "cryptography fehlt für die öffentliche EdDSA-Verifikation."
            ) from error
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(
                base64.b64decode(signature, validate=True), path.read_bytes()
            )
        except Exception as error:
            raise ReleaseError(f"EdDSA-Verifikation fehlgeschlagen: {path.name}") from error

    def _verify_feed_signature(self, payload: bytes, public_key: bytes) -> None:
        match = re.search(
            rb"<!-- sparkle-signatures:\s*edSignature:\s*(\S+)\s*length:\s*(\d+)\s*-->",
            payload,
        )
        if not match:
            raise ReleaseError("Öffentliche Feed-Signatur fehlt.")
        signature = match.group(1).decode("ascii")
        length = int(match.group(2))
        if length <= 0 or length > len(payload):
            raise ReleaseError("Öffentliche Feed-Signaturlänge ist ungültig.")
        with tempfile.NamedTemporaryFile() as source:
            source.write(payload[:length])
            source.flush()
            self._verify_ed25519(Path(source.name), signature, public_key)

    def verify(self, manifest: Manifest) -> None:
        manifest.require("appcast_published")
        tag = str(manifest.data["tag"])
        release = self._remote_release(tag)
        if release is None or release["isDraft"] or not release["isPrerelease"]:
            raise ReleaseError("Öffentlicher GitHub-Release ist kein Pre-Release.")
        if self._resolve_remote_tag_commit(tag) != manifest.data["source_commit"]:
            raise ReleaseError("Öffentlicher Tag zeigt nicht auf den Manifest-Commit.")
        latest = self._gh_json(
            [
                "api",
                f"repos/{self.config['github_repository']}/releases/latest",
            ]
        )
        if latest.get("tag_name") == tag:
            raise ReleaseError("Pilot-Pre-Release wurde unerwartet als Latest markiert.")
        self._verify_remote_assets(manifest, release)
        feed_payload = fetch_bytes(str(self.config["pilot_feed_url"]))
        items = parse_appcast(feed_payload)
        matches = [item for item in items if item["build"] == manifest.data["build"]]
        if len(matches) != 1:
            raise ReleaseError("Öffentlicher Pilot-Appcast enthält den Build nicht eindeutig.")
        item = matches[0]
        if (
            item["version"] != manifest.data["version"]
            or item["architecture"] != self.config["architecture"]
            or item["minimum_macos"] != self.config["minimum_macos"]
        ):
            raise ReleaseError("Öffentliche Pilotmetadaten sind inkonsistent.")
        dmg_name = expected_asset_names(
            self.config, manifest.data["version"], manifest.data["build"]
        )[0]
        expected = next(
            asset for asset in manifest.data["assets"] if asset["name"] == dmg_name
        )
        temporary_root = Path(tempfile.mkdtemp(prefix="jkm-release-verify-"))
        try:
            dmg = temporary_root / dmg_name
            dmg.write_bytes(fetch_bytes(item["url"], timeout=600))
            if (
                dmg.stat().st_size != expected["size"]
                or sha256_file(dmg) != expected["sha256"]
                or item["length"] != expected["size"]
            ):
                raise ReleaseError("Öffentliches DMG weicht vom Manifest ab.")
            public_key = base64.b64decode(
                (ROOT / self.config["sparkle_public_key_file"])
                .read_text(encoding="utf-8")
                .strip(),
                validate=True,
            )
            self._verify_ed25519(dmg, item["signature"], public_key)
            notes = temporary_root / "release-notes.html"
            notes.write_bytes(fetch_bytes(item["release_notes_url"]))
            if notes.stat().st_size != item["release_notes_length"]:
                raise ReleaseError("Öffentliche Release-Notes-Länge weicht ab.")
            self._verify_ed25519(
                notes, item["release_notes_signature"], public_key
            )
            self._verify_feed_signature(feed_payload, public_key)
            stable = self._gh_optional_json(
                [
                    "api",
                    f"repos/{self.config['pilot_appcast_repository']}/contents/stable",
                    "-H",
                    "Accept: application/vnd.github+json",
                ]
            )
            if stable is not None:
                raise ReleaseError("Stable-Verzeichnis ist öffentlich vorhanden.")
            public_manifest = manifest.public_path.read_text(encoding="utf-8")
            if any(marker in public_manifest for marker in PRIVATE_PATH_PATTERNS):
                raise ReleaseError("Veröffentlichtes Manifest enthält private Pfade.")
            if any(pattern.search(public_manifest) for pattern in SECRET_PATTERNS):
                raise ReleaseError("Veröffentlichtes Manifest enthält mögliche Secrets.")
            manifest.complete("remote_verified")
        except Exception as error:
            manifest.fail("remote_verified", error)
            raise
        finally:
            shutil.rmtree(temporary_root, ignore_errors=True)

    def verify_reference_303(self) -> dict[str, Any]:
        reference = self.config["reference_release"]
        tag = str(reference["tag"])
        release = self._remote_release(tag)
        if release is None:
            raise ReleaseError("Referenzrelease Build 303 fehlt.")
        if release["isDraft"] or not release["isPrerelease"]:
            raise ReleaseError("Referenzrelease Build 303 ist kein Pre-Release.")
        if self._resolve_remote_tag_commit(tag) != reference["source_commit"]:
            raise ReleaseError("Build-303-Tag zeigt nicht auf den Referenzcommit.")
        feed = self._remote_appcast()
        matches = [item for item in feed if item["build"] == reference["build"]]
        if len(matches) != 1:
            raise ReleaseError("Pilot-Appcast enthält Build 303 nicht eindeutig.")
        item = matches[0]
        remote_assets = {asset["name"]: asset for asset in release["assets"]}
        expected_assets = {
            asset["name"]: asset for asset in reference.get("assets", [])
        }
        if not expected_assets or set(remote_assets) != set(expected_assets):
            raise ReleaseError("Build-303-Asset-Allowlist weicht von der Referenz ab.")
        for name, expected in expected_assets.items():
            actual = remote_assets[name]
            if (
                int(actual["size"]) != int(expected["size"])
                or str(actual.get("digest", ""))
                != f"sha256:{expected['sha256']}"
            ):
                raise ReleaseError(
                    f"Build-303-Assetmetadaten weichen ab: {name}"
                )
        dmg_assets = [
            asset for name, asset in expected_assets.items() if name.endswith(".dmg")
        ]
        if len(dmg_assets) != 1 or item["length"] != int(dmg_assets[0]["size"]):
            raise ReleaseError("Build-303-DMG-Länge weicht von der Referenz ab.")
        return {
            "status": "already_published",
            "version": reference["version"],
            "build": reference["build"],
            "tag": tag,
            "release": "published_prerelease",
            "pilot_appcast": "active",
            "lower_build_update_eligible": min(item["build"] for item in feed)
            < reference["build"],
            "same_build_republish_blocked": True,
            "stable_enabled": False,
        }


def phase_plan(*, include_build: bool, publish_github: bool, publish_appcast: bool) -> list[str]:
    plan = ["inspect", "prepare"]
    if include_build:
        plan.extend(["build", "package-test"])
    if publish_github:
        plan.append("publish-github")
    if publish_appcast:
        if not publish_github:
            raise ReleaseError("Appcast-Freigabe benötigt auch GitHub-Freigabe.")
        plan.extend(["publish-appcast", "verify"])
    return plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sichere Automation des Jenaplan-Pilot-Releases."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--reference-303", action="store_true")
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--version")
    prepare_parser.add_argument("--build", type=int)
    for name in ("build", "publish-github", "publish-appcast", "verify", "status"):
        phase = subparsers.add_parser(name)
        phase.add_argument("--manifest", type=Path)
    package = subparsers.add_parser("package-test")
    package.add_argument("--manifest", type=Path)
    package.add_argument("--restore-smoke", action="store_true")
    run = subparsers.add_parser("run")
    run.add_argument("--version")
    run.add_argument("--build", type=int)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--build-artifacts", action="store_true")
    run.add_argument("--restore-smoke", action="store_true")
    run.add_argument("--approve-github-publish", action="store_true")
    run.add_argument("--approve-appcast-publish", action="store_true")
    return parser


def render(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = ReleaseConfig.load(args.config)
        automation = ReleasePilot(config)
        if args.command == "inspect":
            report = (
                automation.verify_reference_303()
                if args.reference_303
                else automation.inspect()
            )
            render(report)
            return 0
        if args.command == "prepare":
            manifest = automation.prepare(version=args.version, build=args.build)
            render(sanitize_public(manifest.data))
            return 0
        if args.command == "status":
            render(sanitize_public(load_active_manifest(args.manifest).data))
            return 0
        if args.command == "run":
            plan = phase_plan(
                include_build=args.build_artifacts and not args.dry_run,
                publish_github=args.approve_github_publish and not args.dry_run,
                publish_appcast=args.approve_appcast_publish and not args.dry_run,
            )
            if args.dry_run:
                inspection = automation.inspect(allow_existing=True)
                render(
                    {
                        "dry_run": True,
                        "inspection": inspection,
                        "planned_phases": phase_plan(
                            include_build=args.build_artifacts,
                            publish_github=False,
                            publish_appcast=False,
                        ),
                        "target_assets": expected_asset_names(
                            config,
                            args.version or inspection["version"],
                            args.build or inspection["build"],
                        ),
                        "publishing": "disabled",
                        "sparkle_private_material": "not_accessed",
                    }
                )
                return 0
            manifest = automation.prepare(version=args.version, build=args.build)
            if "build" in plan:
                automation.build(manifest)
                automation.package_test(
                    manifest, restore_smoke=args.restore_smoke
                )
            if "publish-github" in plan:
                automation.publish_github(manifest)
            if "publish-appcast" in plan:
                automation.publish_appcast(manifest)
                automation.verify(manifest)
            render(sanitize_public(manifest.data))
            return 0
        manifest = load_active_manifest(args.manifest)
        if args.command == "build":
            automation.build(manifest)
        elif args.command == "package-test":
            automation.package_test(manifest, restore_smoke=args.restore_smoke)
        elif args.command == "publish-github":
            automation.publish_github(manifest)
        elif args.command == "publish-appcast":
            automation.publish_appcast(manifest)
        elif args.command == "verify":
            automation.verify(manifest)
        render(sanitize_public(manifest.data))
        return 0
    except (ReleaseError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"NO-GO: {redact(str(error))}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
