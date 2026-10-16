"""Read-only domain checks shared by synthetic migration source and backup."""
import json
from .schema_upgrade import UpgradeError
from .timetable import TimetableEntry, TimetableValidator
from .learning_report import snapshot_sha256
from .learning_conference import learning_conference_snapshot_sha256


def timetable_instructional_subject_ids(connection):
    """Actual catalog subjects usable for lessons, excluding development domains."""
    return {row[0] for row in connection.execute("SELECT DISTINCT subject_id FROM competencies")
            if row[0] not in {"selbst_sozialkompetenz", "arbeits_lernkompetenz"}}


def verify_timetable_source_references(connection):
    subjects = timetable_instructional_subject_ids(connection)
    targets = {kind: {row[0] for row in connection.execute(f"SELECT {column} FROM {table}")}
               for kind, table, column in (("group", "groups", "group_id"),
                   ("course", "courses", "course_id"), ("course_group", "course_groups", "course_group_id"))}
    entries = tuple(TimetableEntry(**dict(row)) for row in connection.execute("SELECT * FROM timetable_entries"))
    try:
        for entry in entries:
            if not isinstance(entry.timetable_entry_id, str) or not entry.timetable_entry_id.strip():
                raise ValueError
            TimetableValidator().validate(entry, valid_subject_ids=subjects,
                valid_target_ids=targets, existing_entries=entries)
        for table, hash_function in (("learning_report_revisions", snapshot_sha256),
                ("learning_conference_revisions", learning_conference_snapshot_sha256)):
            for version, payload, digest in connection.execute(
                    f"SELECT snapshot_schema_version, snapshot_json, snapshot_sha256 FROM {table}"):
                if version != 1 or hash_function(payload) != digest or not isinstance(json.loads(payload), dict):
                    raise ValueError
    except Exception:
        raise UpgradeError("upgrade_domain_reference_invalid") from None


def verify_timetable_target_references(connection):
    """Independently validate normalized target, including inactive history."""
    subjects = timetable_instructional_subject_ids(connection)
    targets = {kind: {row[0] for row in connection.execute(f"SELECT {column} FROM {table}")}
               for kind, table, column in (("group", "groups", "group_id"),
                   ("course", "courses", "course_id"), ("course_group", "course_groups", "course_group_id"))}
    rows = tuple(dict(row) for row in connection.execute("SELECT * FROM timetable_entries"))
    links = {}
    for entry_id, subject_id in connection.execute("SELECT timetable_entry_id, subject_id FROM timetable_entry_subjects"):
        links.setdefault(entry_id, []).append(subject_id)
    try:
        ids = {row["timetable_entry_id"] for row in rows}
        if set(links) - ids:
            raise ValueError
        for row in rows:
            entry_id = row["timetable_entry_id"]
            selected = links.get(entry_id, [])
            if not isinstance(entry_id, str) or not entry_id.strip():
                raise ValueError
            if row["entry_kind"] == "subject_lesson":
                if not selected or len(set(selected)) != len(selected) or not set(selected) <= subjects:
                    raise ValueError
            elif row["entry_kind"] == "homeroom_session":
                if selected or row["target_type"] != "group":
                    raise ValueError
            else:
                raise ValueError
            if row["target_id"] not in targets.get(row["target_type"], set()):
                raise ValueError
            start = TimetableValidator.parse_time(row["start_time"], "Beginn")
            end = TimetableValidator.parse_time(row["end_time"], "Ende")
            if (row["weekday"] not in range(1, 6) or start >= end
                    or row["active"] not in (0, 1) or row["sort_order"] < 0):
                raise ValueError
            if row["active"]:
                for other in rows:
                    if (other["active"] and other["timetable_entry_id"] != entry_id
                            and other["weekday"] == row["weekday"]
                            and start < TimetableValidator.parse_time(other["end_time"], "Ende")
                            and end > TimetableValidator.parse_time(other["start_time"], "Beginn")):
                        raise ValueError
        for table, hash_function in (("learning_report_revisions", snapshot_sha256),
                ("learning_conference_revisions", learning_conference_snapshot_sha256)):
            for version, payload, digest in connection.execute(
                    f"SELECT snapshot_schema_version, snapshot_json, snapshot_sha256 FROM {table}"):
                if version != 1 or hash_function(payload) != digest or not isinstance(json.loads(payload), dict):
                    raise ValueError
    except Exception:
        raise UpgradeError("upgrade_domain_reference_invalid") from None
