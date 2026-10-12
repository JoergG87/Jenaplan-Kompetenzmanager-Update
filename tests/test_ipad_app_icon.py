"""Native iOS icon packaging preserves its source and covers iPad sizes."""
import json
import shutil

from PIL import Image

from scripts.build_ipad_app import ROOT, configure_ipad_icon


def test_native_icon_is_opaque_complete_and_idempotent(tmp_path):
    (tmp_path / 'assets').mkdir()
    source = tmp_path / 'assets/app_icon.png'
    shutil.copy2(ROOT / 'assets/app_icon.png', source)
    original = source.read_bytes()
    project = tmp_path / 'deployment/ios/Test.xcodeproj/project.pbxproj'
    project.parent.mkdir(parents=True)
    project.write_text('''/* Begin PBXBuildFile section */
/* End PBXBuildFile section */
/* Begin PBXFileReference section */
/* End PBXFileReference section */
{isa = PBXResourcesBuildPhase; files = ();}
ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
''')
    configure_ipad_icon(tmp_path, project)
    configured = project.read_text()
    configure_ipad_icon(tmp_path, project)
    assert project.read_text() == configured
    assert source.read_bytes() == original
    assert configured.count('isa = PBXBuildFile') == 1
    assert configured.count('isa = PBXFileReference') == 1
    catalog = project.parent.parent / 'Assets.xcassets/AppIcon.appiconset'
    entries = json.loads((catalog / 'Contents.json').read_text())['images']
    assert any(e['idiom'] == 'ipad' and e['size'] == '83.5x83.5' for e in entries)
    assert any(e['idiom'] == 'ios-marketing' for e in entries)
    for entry in entries:
        with Image.open(catalog / entry['filename']) as image:
            pixels = int(float(entry['size'].split('x')[0]) * int(entry['scale'][:-1]))
            assert image.size == (pixels, pixels)
            assert image.mode == 'RGB'
    with Image.open(catalog / 'icon-1024.png') as image:
        assert image.getpixel((0, 0)) == (255, 255, 255)
