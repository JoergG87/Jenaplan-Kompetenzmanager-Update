"""Stage the complete governed AppShell for isolated iPad simulator packaging."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def stage_app(target: Path):
    from scripts.seed_test_data import seed_test_data
    target = Path(target).absolute()
    from src.core.runtime_root_protection import require_unprotected_output_path
    if target in (ROOT, *ROOT.parents) or any(p.is_symlink() for p in (target, *target.parents)):
        raise ValueError('Unsicherer iPad-Stagingordner.')
    require_unprotected_output_path(target)
    # Never overwrite a checkout, existing build or product folder.
    if target.exists() and any(target.iterdir()):
        raise ValueError('Der iPad-Stagingordner muss leer sein.')
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'src', target / 'src', ignore=shutil.ignore_patterns('__pycache__', '*_html'))
    (target / 'prototypes' / 'pdf_engine').mkdir(parents=True)
    shutil.copy2(ROOT / 'prototypes/pdf_engine/output_models.py', target / 'prototypes/pdf_engine/output_models.py')
    shutil.copytree(ROOT / 'assets', target / 'assets', ignore=shutil.ignore_patterns('*.zip'))
    (target / 'data').mkdir()
    shutil.copy2(ROOT / 'data/curriculum_catalog_v1.csv', target / 'data/curriculum_catalog_v1.csv')
    (target / 'main.py').write_text('from src.tablet_app.main import main\nraise SystemExit(main())\n')
    with tempfile.TemporaryDirectory(prefix='jkm-ipad-template-') as temporary:
        db = Path(temporary) / 'runtime' / 'kompetenzmanager.sqlite'
        result = seed_test_data(db, teacher_name='Test-Lehrkraft')
        template = target / 'tablet-template'
        template.mkdir()
        shutil.copy2(db, template / db.name)
        if (db.parent / 'documents').exists():
            shutil.copytree(db.parent / 'documents', template / 'documents')
        manifest = {'format': 1, 'synthetic_only': True,
                    'sha256': hashlib.sha256((template / db.name).read_bytes()).hexdigest(),
                    'students': result.student_count, 'observations': result.observation_count}
        (template / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return target


def configure_project(target: Path, xcframework: Path, wheels: list[Path]):
    """Copy immutable resources and signed iOS extensions into the app bundle."""
    import re
    import shlex
    import zipfile
    packages = target / 'python_packages'
    packages.mkdir(exist_ok=True)
    for wheel in wheels:
        with zipfile.ZipFile(wheel) as archive:
            if any(Path(name).is_absolute() or '..' in Path(name).parts for name in archive.namelist()):
                raise ValueError('Unsicherer Paketpfad im Wheel.')
            archive.extractall(packages)
    # The same existing renderer is shared with desktop, not substituted.
    shutil.copy2(ROOT / 'prototypes/pdf_engine/renderer.py', target / 'prototypes/pdf_engine/renderer.py')
    project = next((target / 'deployment').glob('*/Jenaplan-iPad-App-Test.xcodeproj/project.pbxproj'))
    scripts = list(re.finditer(r'shellScript = "(?:[^"\\]|\\.)*";', project.read_text()))
    match = scripts[-1]
    extra = 'set -e\n'
    for name in ('assets', 'data', 'tablet-template', 'prototypes', 'src'):
        extra += f'rsync -a --delete {shlex.quote(str(target / name))}/ "$CODESIGNING_FOLDER_PATH/{name}/"\n'
    extra += f'rsync -a {shlex.quote(str(packages))}/ "$CODESIGNING_FOLDER_PATH/packages/"\n'
    relative = os.path.relpath(xcframework, project.parent.parent)
    extra += f'source "$PROJECT_DIR"/{shlex.quote(relative)}/build/utils.sh\n'
    extra += f'process_dylibs {shlex.quote(relative)} packages\n'
    text = project.read_text()
    old = json.loads(match.group(0)[len('shellScript = '):-1])
    text = text[:match.start()] + 'shellScript = ' + json.dumps(old + extra) + ';' + text[match.end():]
    project.write_text(text)
    native = project.parent.parent / 'main.mm'
    content = native.read_text()
    shutil.copy2(target / 'src/tablet_app/native_share.mm', native.parent / 'native_share.mm')
    include = '#include "native_share.mm"\n'
    if include not in content:
        content = include + content
        content = content.replace('    PyImport_AppendInittab("PySide6.QtCore", PyInit_QtCore);',
            '    PyImport_AppendInittab("jkm_ios_share", PyInit_jkm_ios_share);\n    PyImport_AppendInittab("PySide6.QtCore", PyInit_QtCore);')
        native.write_text(content)
    return project


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True, type=Path)
    parser.add_argument('--deploy-tool', type=Path)
    parser.add_argument('--pyside-wheel', type=Path)
    parser.add_argument('--shiboken-wheel', type=Path)
    parser.add_argument('--python-xcframework', type=Path)
    parser.add_argument('--dependency-wheel', type=Path, action='append', default=[])
    args = parser.parse_args()
    target = stage_app(args.stage)
    if args.deploy_tool:
        if not all((args.pyside_wheel, args.shiboken_wheel, args.python_xcframework)):
            parser.error('Deployment benötigt beide iOS-Wheels und Python.xcframework.')
        # Explicit modules exclude desktop-only WebEngine, with native PDF viewer.
        import configparser
        spec = configparser.ConfigParser()
        spec.read_dict({
            'app': {'title': 'Jenaplan-iPad-App-Test', 'project_dir': '.',
                    'input_file': 'main.py', 'exec_directory': '.', 'project_file': '', 'icon': ''},
            'python': {'packages': 'Nuitka==4.1.1', 'android_packages': ''},
            'qt': {'qml_files': '', 'excluded_qml_plugins': '', 'modules': '', 'plugins': ''},
            'android': {'wheel_pyside': '', 'wheel_shiboken': '', 'plugins': ''},
            'ios': {'wheel_pyside': '', 'wheel_shiboken': '', 'xcframework_path': '',
                    'bundle_id': '', 'team_id': '', 'version': '1.0',
                    'deployment_target': '', 'entitlements': '',
                    'signing_style': 'Automatic', 'header_search_paths': ''},
            'nuitka': {'macos.permissions': '', 'mode': 'standalone', 'extra_args': ''},
            'buildozer': {'mode': 'debug', 'recipe_dir': '', 'jars_dir': '',
                          'ndk_path': '', 'sdk_path': '', 'local_libs': '', 'arch': ''},
        })
        spec['app']['title'] = 'Jenaplan-iPad-App-Test'
        spec['app']['project_dir'] = '.'
        spec['qt']['modules'] = 'Core,Gui,Widgets,Svg,Pdf,PdfWidgets'
        spec['ios']['bundle_id'] = 'de.jenaplan.kompetenzmanager.ipad-app-test'
        spec['ios']['wheel_pyside'] = str(args.pyside_wheel.resolve())
        spec['ios']['wheel_shiboken'] = str(args.shiboken_wheel.resolve())
        spec['ios']['xcframework_path'] = str(args.python_xcframework.resolve())
        with (target / 'pysidedeploy.spec').open('w') as output:
            spec.write(output)
        subprocess.run([str(args.deploy_tool.resolve()), 'main.py', '--wheel-pyside', str(args.pyside_wheel.resolve()), '--wheel-shiboken', str(args.shiboken_wheel.resolve()), '--xcframework-path', str(args.python_xcframework.resolve()), '--name', 'Jenaplan-iPad-App-Test', '--bundle-id', 'de.jenaplan.kompetenzmanager.ipad-app-test'], cwd=target, check=True)
        configure_project(target, args.python_xcframework.resolve(), args.dependency_wheel)
    print(target)


if __name__ == '__main__':
    main()
