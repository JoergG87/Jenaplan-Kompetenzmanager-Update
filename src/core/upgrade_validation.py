"""Read-only domain checks shared by synthetic migration source and backup."""
import json
from .schema_upgrade import UpgradeError
from .timetable import TimetableEntry, TimetableValidator
from .learning_report import snapshot_sha256
from .learning_conference import learning_conference_snapshot_sha256


def verify_timetable_source_references(connection):
    subjects = {row[0] for row in connection.execute("SELECT DISTINCT subject_id FROM competencies")}
    targets = {kind: {row[0] for row in connection.execute(f"SELECT {column} FROM {table}")}
               for kind, table, column in (("group", "groups", "group_id"),
                   ("course", "courses", "course_id"), ("course_group", "course_groups", "course_group_id"))}
    entries = tuple(TimetableEntry(**dict(row)) for row in connection.execute("SELECT * FROM timetable_entries"))
    try:
        for entry in entries:
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
