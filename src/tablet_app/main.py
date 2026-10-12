"""Full original app UI in a separate synthetic iPad container."""
import json
import os
from pathlib import Path
import sys
os.environ['PYSIDE6_OPTION_LAZY'] = '0'
from PySide6.QtWidgets import QApplication, QMessageBox
from src.tablet_app.runtime import TabletRuntime, tablet_data_root
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.runtime import resource_path, runtime_paths
from src.desktop_app.theme import apply_app_theme
from src.tablet_app.shell import TabletAppShell


def main():
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    app.setOrganizationName('JenaplanTabletTest')
    app.setApplicationName('JenaplanTabletAppTest')
    # This build contains the governed Qt views, never the optional web hosts.
    os.environ['JKM_REPORT_UI'] = 'qt'
    os.environ['JKM_LEG_UI'] = 'qt'
    if sys.platform == 'ios':
        from jkm_ios_share import install_test_accessibility_mode
        install_test_accessibility_mode()
        from src.tablet_app.dialogs import install_tablet_message_port
        install_tablet_message_port()
    from src.desktop_app.motion import set_reduced_motion
    set_reduced_motion(True)
    apply_app_theme(app)
    try:
        manifest = json.loads(resource_path('tablet-template', 'manifest.json').read_text())
        runtime = TabletRuntime(tablet_data_root(), resource_path('tablet-template', 'kompetenzmanager.sqlite'), manifest['sha256'])
        paths = runtime_paths(runtime.root)
        for path in (paths.exports, paths.backups):
            if path.is_symlink():
                raise ValueError('Unsicherer Tablet-Testordner.')
            path.mkdir(exist_ok=True)
        adapter = StudentDesktopAdapter(database=runtime.database)
        window = TabletAppShell(runtime.database_path, paths=paths, student_adapter=adapter, backup_restore_available=False)
    except Exception as error:
        QMessageBox.critical(None, 'iPad-Test konnte nicht geöffnet werden', str(error))
        return 1
    window.showMaximized()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
