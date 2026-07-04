"""Runtime command adapter for the Jenaplan Kompetenzmanager."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from src.application.commands import CreateStudentCommand
from src.application.dispatcher import (
    ApplicationCommandDispatcher,
    ErrorResult,
    SuccessResult,
    student_create_handler,
)
from src.core.sqlite_store import (
    SQLITE_SPIKE_PATH,
    SQLiteCourseRepository,
    SQLiteDatabase,
    SQLiteGroupRepository,
    SQLiteStudentRepository,
    create_sqlite_seed_database,
)
from src.core.student import StudentService, StudentValidator
from src.core.workbook_data import StudentRecord


COMMAND_STUDENT_CREATE = "student.create"


def main(argv: list[str] | None = None) -> int:
    """Run a runtime command and write a structured result."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.area == "student" and args.action == "create":
        result = run_student_create(args)
    else:
        result = ErrorResult(
            COMMAND_STUDENT_CREATE,
            "Unbekannter Runtime-Command.",
            "RuntimeCommandError",
        )

    result_payload = _result_payload(result)
    result_text = json.dumps(result_payload, ensure_ascii=False, indent=2)
    if args.result_file:
        result_path = Path(args.result_file)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(result_text + "\n", encoding="utf-8")
    else:
        print(result_text)

    return 0 if result_payload["success"] else 1


def run_student_create(args: argparse.Namespace) -> object:
    """Create a student through the application command stack."""
    try:
        database = _runtime_database(Path(args.database))
        payload = _student_create_payload(args)
        command = CreateStudentCommand(
            first_name=payload["first_name"],
            last_name=payload["last_name"],
            group_id=_resolve_group_id(database, payload["group"]),
            course_id=_resolve_course_id(database, payload["course"]),
            student_notes=payload["student_notes"],
        )
        dispatcher = _student_dispatcher(database)
        return dispatcher.dispatch(command)
    except Exception as exc:
        return ErrorResult(COMMAND_STUDENT_CREATE, str(exc), type(exc).__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jenaplan Kompetenzmanager Runtime Adapter")
    parser.add_argument("--database", default=str(SQLITE_SPIKE_PATH))
    parser.add_argument("--result-file", default="")

    subparsers = parser.add_subparsers(dest="area", required=True)
    student_parser = subparsers.add_parser("student")
    student_subparsers = student_parser.add_subparsers(dest="action", required=True)

    create_parser = student_subparsers.add_parser("create")
    create_parser.add_argument("--command-file", default="")
    create_parser.add_argument("--first-name", default="")
    create_parser.add_argument("--last-name", default="")
    create_parser.add_argument("--group", default="")
    create_parser.add_argument("--course", default="")
    create_parser.add_argument("--student-notes", default="")
    return parser


def _runtime_database(path: Path) -> SQLiteDatabase:
    if not path.exists():
        return create_sqlite_seed_database(path)
    database = SQLiteDatabase(path)
    database.initialize_schema()
    return database


def _student_dispatcher(database: SQLiteDatabase) -> ApplicationCommandDispatcher:
    student_repository = SQLiteStudentRepository(database)
    group_ids = tuple(group.group_id for group in SQLiteGroupRepository(database).list_groups())
    course_ids = tuple(course.course_id for course in SQLiteCourseRepository(database).list_courses())
    service = StudentService(
        student_repository,
        StudentValidator(),
        group_ids,
        course_ids,
    )
    dispatcher = ApplicationCommandDispatcher()
    dispatcher.register(COMMAND_STUDENT_CREATE, student_create_handler(service))
    return dispatcher


def _student_create_payload(args: argparse.Namespace) -> dict[str, str]:
    payload = {
        "first_name": args.first_name,
        "last_name": args.last_name,
        "group": args.group,
        "course": args.course,
        "student_notes": args.student_notes,
    }
    if args.command_file:
        command_payload = json.loads(_read_command_file(Path(args.command_file)))
        if command_payload.get("command") != COMMAND_STUDENT_CREATE:
            raise ValueError(f"Ungueltiger Runtime-Command: {command_payload.get('command')}")
        data = command_payload.get("data", {})
        if not isinstance(data, dict):
            raise ValueError("Runtime-Command enthaelt kein gueltiges data-Objekt.")
        payload.update(
            {
                "first_name": _text(data.get("first_name", payload["first_name"])),
                "last_name": _text(data.get("last_name", payload["last_name"])),
                "group": _text(data.get("group", data.get("group_id", payload["group"]))),
                "course": _text(data.get("course", data.get("course_id", payload["course"]))),
                "student_notes": _text(data.get("student_notes", payload["student_notes"])),
            }
        )
    return payload


def _resolve_group_id(database: SQLiteDatabase, group_value: str) -> str:
    cleaned_value = group_value.strip()
    for group in SQLiteGroupRepository(database).list_groups():
        if cleaned_value in (group.group_id, group.group_name):
            return group.group_id
    return cleaned_value


def _read_command_file(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "mac_roman", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8")


def _resolve_course_id(database: SQLiteDatabase, course_value: str) -> str:
    cleaned_value = course_value.strip()
    for course in SQLiteCourseRepository(database).list_courses():
        if cleaned_value in (course.course_id, course.course_name):
            return course.course_id
    return cleaned_value


def _result_payload(result: object) -> dict[str, Any]:
    if isinstance(result, SuccessResult):
        payload = {
            "success": True,
            "command_name": result.command_name,
            "message": "Schueler wurde in SQLite gespeichert.",
        }
        payload.update(_student_result_payload(result.value))
        return payload
    if isinstance(result, ErrorResult):
        return {
            "success": False,
            "command_name": result.command_name,
            "error_type": result.error_type,
            "message": result.message,
        }
    return {
        "success": False,
        "command_name": COMMAND_STUDENT_CREATE,
        "error_type": "RuntimeResultError",
        "message": f"Unerwartetes Runtime-Ergebnis: {type(result).__name__}",
    }


def _student_result_payload(value: object) -> dict[str, Any]:
    if isinstance(value, StudentRecord):
        return {"student": asdict(value), "student_id": value.student_id}
    if is_dataclass(value):
        data = asdict(value)
        return {"value": data}
    return {"value": value}


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


if __name__ == "__main__":
    sys.exit(main())
