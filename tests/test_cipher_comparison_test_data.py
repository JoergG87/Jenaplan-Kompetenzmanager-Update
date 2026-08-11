from __future__ import annotations

from contextlib import closing
from pathlib import Path

from scripts.seed_test_data import seed_cipher_pilot_test_data
from src.core.database_engine import (
    SQLCIPHER_4_17_BINDING_VERSION,
    SQLCIPHER_4_17_ENGINE_VERSION,
    SQLCipherConnectionProvider,
)
from src.desktop_app.adapters.curriculum_desktop_adapter import (
    CurriculumDesktopAdapter,
)
from src.desktop_app.view_models.observation_view_model import (
    rating_chip_options_for_competency,
    rating_profile_for_competency,
)
from src.security.final_v4_backup_runtime import (
    build_final_v4_encrypted_backup_service,
)
from tests.test_cipher_product_composition import _case, _open, requires_exact_417


EXPECTED_COMPETENCY_IDS = tuple(
    f"CMP-{100000 + index:06d}" for index in range(1, 332)
)
EXPECTED_RATING_TOKENS = {"--", "-", "+", "++"}
REQUIRED_TEACHING_SUBJECTS = {
    "deutsch",
    "mathematik",
    "sport",
    "kreatives_gestalten",
    "englisch",
}


def _semantic_snapshot(database) -> tuple[tuple[object, ...], ...]:
    with closing(database.connect()) as connection:
        return tuple(
            tuple(row)
            for query in (
                """
                SELECT first_name, last_name
                FROM students ORDER BY last_name, first_name
                """,
                """
                SELECT student.last_name, profile.school_year_id, profile.mode
                FROM student_documentation_subject_profiles AS profile
                JOIN students AS student ON student.student_id = profile.student_id
                ORDER BY student.last_name
                """,
                """
                SELECT student.last_name, selection.school_year_id,
                       selection.subject_id
                FROM student_documentation_subject_selections AS selection
                JOIN students AS student ON student.student_id = selection.student_id
                ORDER BY student.last_name, selection.subject_id
                """,
                """
                SELECT student.last_name, observation.date, observation.subject_id,
                       observation.context, observation.note
                FROM observations AS observation
                JOIN students AS student
                  ON student.student_id = observation.student_id
                ORDER BY student.last_name, observation.date,
                         observation.subject_id
                """,
                """
                SELECT student.last_name, observation.date, rating.competency_id,
                       rating.subject_id, rating.rating
                FROM observation_competency_ratings AS rating
                JOIN observations AS observation
                  ON observation.observation_id = rating.observation_id
                JOIN students AS student
                  ON student.student_id = observation.student_id
                ORDER BY student.last_name, observation.date,
                         rating.competency_id
                """,
                """
                SELECT student.last_name, draft.period_start, draft.period_end
                FROM report_drafts AS draft
                JOIN students AS student ON student.student_id = draft.student_id
                ORDER BY student.last_name, draft.period_start
                """,
                """
                SELECT student.last_name, draft.period_start, draft.period_end,
                       draft.conference_date
                FROM learning_conference_drafts AS draft
                JOIN students AS student ON student.student_id = draft.student_id
                ORDER BY student.last_name, draft.period_start
                """,
            )
            for row in connection.execute(query).fetchall()
        )


@requires_exact_417
def test_fresh_cipher_product_start_remains_free_of_comparison_data(
    tmp_path: Path,
) -> None:
    paths, account, store = _case(tmp_path)

    opened = _open(paths, account, store, first_run_allowed=True)
    from src.desktop_app.main import _build_cipher_product_student_adapter

    _build_cipher_product_student_adapter(opened)

    with closing(opened.database.connect()) as connection:
        assert tuple(connection.execute(
            """
            SELECT label, start_date, end_date, status
            FROM school_years
            """
        ).fetchone()) == ("2026/27", "2026-08-01", "2027-07-31", "current")
        assert connection.execute(
            "SELECT COUNT(*) FROM competencies"
        ).fetchone()[0] == 331
        for table in (
            "students",
            "groups",
            "courses",
            "student_school_year_assignments",
            "observations",
            "report_drafts",
            "learning_conference_drafts",
            "documents",
            "student_documentation_subject_profiles",
        ):
            assert connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0] == 0
    assert not tuple(paths.root.rglob("*.jkmedoc"))
    assert not tuple(paths.root.rglob("*.jkmebackup"))


@requires_exact_417
def test_comparison_seed_covers_catalog_profiles_workflows_and_encrypted_storage(
    tmp_path: Path,
) -> None:
    paths, account, store = _case(tmp_path)
    opened = _open(paths, account, store, first_run_allowed=True)

    result = seed_cipher_pilot_test_data(opened, source_root=paths.root)

    assert result.student_count == 24
    assert result.observation_count == 71
    assert result.document_count == 5
    assert result.timetable_count == 10
    assert result.report_draft_count == 2
    assert result.report_revision_count == 1
    assert result.conference_draft_count == 2
    assert result.conference_revision_count == 1

    restarted = _open(paths, account, store, first_run_allowed=False)
    with closing(restarted.database.connect()) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 4
        catalog = connection.execute(
            """
            SELECT competency_id, subject_id, learning_area, competency_group,
                   catalog_status, active
            FROM competencies
            ORDER BY sort_order, competency_id
            """
        ).fetchall()
        assert tuple(row[0] for row in catalog) == EXPECTED_COMPETENCY_IDS
        assert len({row[1] for row in catalog}) == 12
        assert len({(row[1], row[2]) for row in catalog}) == 48
        assert len({(row[1], row[2], row[3]) for row in catalog}) == 81
        assert all(row[4] == "current" and row[5] == 1 for row in catalog)
        assert not any(row[0].startswith("CMP-000") for row in catalog)

        assert connection.execute("SELECT COUNT(*) FROM groups").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 3
        assert connection.execute(
            "SELECT COUNT(*) FROM student_school_year_assignments"
        ).fetchone()[0] == 24
        observation_counts = connection.execute(
            """
            SELECT student_id, COUNT(*)
            FROM observations GROUP BY student_id ORDER BY student_id
            """
        ).fetchall()
        assert len(observation_counts) == 24
        assert min(row[1] for row in observation_counts) == 2
        assert max(row[1] for row in observation_counts) == 3

        empty_student_id = connection.execute(
            """
            SELECT profile.student_id
            FROM student_documentation_subject_profiles AS profile
            LEFT JOIN student_documentation_subject_selections AS selection
              ON selection.student_id = profile.student_id
             AND selection.school_year_id = profile.school_year_id
            WHERE profile.mode = 'custom'
            GROUP BY profile.student_id
            HAVING COUNT(selection.subject_id) = 0
            """
        ).fetchone()[0]
        empty_student_subjects = {
            row[0]
            for row in connection.execute(
                "SELECT subject_id FROM observations WHERE student_id = ?",
                (empty_student_id,),
            ).fetchall()
        }
        assert empty_student_subjects == {
            "selbst_sozialkompetenz",
            "arbeits_lernkompetenz",
        }
        profile_sizes = connection.execute(
            """
            SELECT profile.student_id, COUNT(selection.subject_id)
            FROM student_documentation_subject_profiles AS profile
            LEFT JOIN student_documentation_subject_selections AS selection
              ON selection.student_id = profile.student_id
             AND selection.school_year_id = profile.school_year_id
            GROUP BY profile.student_id ORDER BY profile.student_id
            """
        ).fetchall()
        assert sorted(row[1] for row in profile_sizes) == [0, 2, 2, 2, 3, 5]

        observed_subjects = {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT subject_id FROM observations"
            ).fetchall()
        }
        assert REQUIRED_TEACHING_SUBJECTS.issubset(observed_subjects)
        assert {
            "selbst_sozialkompetenz",
            "arbeits_lernkompetenz",
        }.issubset(observed_subjects)
        assert tuple(connection.execute(
            "SELECT MIN(date), MAX(date) FROM observations"
        ).fetchone()) == ("2026-09-01", "2027-05-24")

        tokens_by_subject = {
            subject_id: {
                row[0]
                for row in connection.execute(
                    """
                    SELECT DISTINCT rating
                    FROM observation_competency_ratings
                    WHERE subject_id = ?
                    """,
                    (subject_id,),
                ).fetchall()
            }
            for subject_id in (
                "selbst_sozialkompetenz",
                "arbeits_lernkompetenz",
                "sport",
            )
        }
        assert all(
            tokens == EXPECTED_RATING_TOKENS
            for tokens in tokens_by_subject.values()
        )
        assert connection.execute("SELECT COUNT(*) FROM report_drafts").fetchone()[0] == 2
        assert connection.execute(
            "SELECT COUNT(*) FROM learning_report_revisions"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM learning_report_pdf_artifacts"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM learning_conference_drafts"
        ).fetchone()[0] == 2
        assert connection.execute(
            "SELECT COUNT(*) FROM learning_conference_revisions"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM learning_conference_pdf_artifacts"
        ).fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 5
        assert {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT document_type FROM documents"
            ).fetchall()
        } == {"Arbeitsprobe", "Lernzielkontrolle", "Gesprächsnotiz", "Bericht"}
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

    entries = CurriculumDesktopAdapter(database=restarted.database).list_entries()
    entry_by_subject = {
        entry.subject_key: entry
        for entry in entries
        if entry.subject_key in {"deutsch", "selbst_sozialkompetenz", "sport"}
    }
    assert rating_profile_for_competency(entry_by_subject["deutsch"]) == "standard"
    assert rating_profile_for_competency(
        entry_by_subject["selbst_sozialkompetenz"]
    ) == "social"
    assert rating_profile_for_competency(entry_by_subject["sport"]) == "sport"
    assert dict(rating_chip_options_for_competency(
        entry_by_subject["selbst_sozialkompetenz"]
    )) == {
        "++": "Ausgeprägt", "+": "Gut", "-": "Teilweise", "--": "Kaum vorhanden"
    }
    assert dict(rating_chip_options_for_competency(entry_by_subject["sport"])) == {
        "++": "Sicher", "+": "Meist", "-": "Übt noch", "--": "Erste Übungen"
    }

    provider = SQLCipherConnectionProvider(
        expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
        expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION,
    )
    service = build_final_v4_encrypted_backup_service(
        opened_runtime=restarted.runtime,
        account_loader=lambda: account,
        environ={},
        key_store=store,
        sqlcipher_provider=provider,
        product_root=paths.root,
    )
    paths.backups.mkdir(mode=0o700)
    backup = service.create(paths.backups / "comparison-test.jkmebackup")
    verified = service.verify(backup.path)
    restore_parent = paths.root / "encrypted-restore-staging"
    restore_parent.mkdir(mode=0o700)
    staged = service.restore_staging(
        backup.path,
        restore_parent / "comparison-verification",
    )
    ready = service.verify_restore_ready(
        staged.staging_root,
        expected_container_sha256=verified.container_sha256,
    )
    preview = service.restore_preview_counts(
        ready.staging_root,
        expected_container_sha256=verified.container_sha256,
    )
    assert staged.state == "RESTORE_READY"
    assert ready.ready_path.is_file()
    assert preview.students == 24
    assert preview.observations == 71
    assert preview.managed_documents == 7
    assert backup.path.suffix == ".jkmebackup"
    assert not backup.path.read_bytes().startswith((b"PK\x03\x04", b"SQLite format 3\x00"))
    assert not paths.final_v4_database.read_bytes().startswith(b"SQLite format 3\x00")
    assert not paths.document_companion_database.read_bytes().startswith(
        b"SQLite format 3\x00"
    )
    managed_files = tuple(paths.encrypted_document_storage.rglob("*.jkmedoc"))
    assert len(managed_files) == 7
    for path in managed_files:
        payload = path.read_bytes()
        assert not payload.startswith(b"%PDF")
        assert b"Synthetisch" not in payload
        assert b"synthetisch" not in payload
    assert not tuple(paths.root.rglob("*.pdf"))
    assert not tuple(paths.root.rglob("*.txt"))


@requires_exact_417
def test_comparison_seed_is_semantically_reproducible(tmp_path: Path) -> None:
    snapshots = []
    for name in ("first", "second"):
        case_root = tmp_path / name
        case_root.mkdir()
        paths, account, store = _case(case_root)
        opened = _open(paths, account, store, first_run_allowed=True)
        seed_cipher_pilot_test_data(opened, source_root=paths.root)
        snapshots.append(_semantic_snapshot(opened.database))

    assert snapshots[0] == snapshots[1]
