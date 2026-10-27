"""Small synthetic-widget timing probe shared by source and sealed package checks."""
from datetime import timedelta
from time import perf_counter
import cProfile
import pstats


def measure_week_actions(shell, app, instant):
    """Measure completion including paint; restore a confirmed B exception."""
    from PySide6.QtCore import QDate
    screen = shell.settings_screen
    shell.show_timetable_settings()
    screen.timetable_week_date.setDate(QDate(instant.date()))
    screen.timetable_week_preview.setCurrentIndex(0)
    app.processEvents()
    measurements = {}
    actions = {
        "preview": lambda i: screen.timetable_week_preview.setCurrentIndex(1 + i % 2),
        "navigate": lambda i: screen.timetable_week_date.setDate(QDate(instant.date() + timedelta(weeks=1 if i % 2 == 0 else 0))),
        "set_override": lambda i: screen.timetable_override_requested.emit(instant.date(), "A" if i % 2 else "B"),
        "clear_override": lambda i: screen.timetable_override_clear_requested.emit(instant.date()),
    }
    for name, action in actions.items():
        if name in ("set_override", "clear_override"):
            screen.timetable_week_date.setDate(QDate(instant.date()))
            screen.timetable_week_preview.setCurrentIndex(0)
            app.processEvents()
        samples = []
        profiles = []
        for i in range(3):
            if name == "clear_override":
                shell.set_timetable_week_override(instant.date(), "B")
            profile = cProfile.Profile()
            start = perf_counter()
            profile.enable()
            action(i)
            app.processEvents()
            profile.disable()
            samples.append(round((perf_counter() - start) * 1000, 3))
            stats = pstats.Stats(profile)
            profiles.append([
                {"file": key[0].split("/")[-1], "function": key[2], "calls": values[1],
                 "total_ms": round(values[3] * 1000, 3), "self_ms": round(values[2] * 1000, 3)}
                for key, values in sorted(stats.stats.items(), key=lambda item: item[1][3], reverse=True)
                if key[2] in {"connect", "_subject_options", "_target_options", "week_view_model", "snapshot",
                    "refresh_dashboard", "set_timetable", "_write", "_render_selected_timetable_day", "dashboard_documentation_refresh"}
            ])
        measurements[name] = {"samples_ms": samples, "max_ms": max(samples), "profiles": profiles}
    screen.timetable_week_date.setDate(QDate(instant.date()))
    screen.timetable_week_preview.setCurrentIndex(0)
    shell.set_timetable_week_override(instant.date(), "B")
    app.processEvents()
    return measurements
