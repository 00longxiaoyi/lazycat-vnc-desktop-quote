#!/usr/bin/env python3
"""Prepare the supplied app without executing it; restore its exact Electron runtime."""
import argparse
import hashlib
import json
import pathlib
import re
import shutil
import struct
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = '33.4.11'
RUNTIME_SHA256 = '212d431c7c916292311c797cd91f84467c5abd6e6983cf24b162efff64cee8a9'
URL = f'https://github.com/electron/electron/releases/download/v{VERSION}'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unpack_asar(data, dest):
    header_size = struct.unpack_from('<I', data, 4)[0]
    json_size = struct.unpack_from('<I', data, 12)[0]
    header = json.loads(data[16:16 + json_size])
    content_offset = 8 + header_size

    def walk(files, parent):
        for name, item in files.items():
            if name in ('.', '..') or '/' in name or '\\' in name:
                raise ValueError(f'Unsafe ASAR entry: {name}')
            target = parent / name
            if 'files' in item:
                target.mkdir(parents=True, exist_ok=True)
                walk(item['files'], target)
            else:
                if item.get('unpacked') or 'link' in item:
                    raise ValueError(f'Unsupported ASAR entry: {name}')
                start = content_offset + int(item['offset'])
                payload = data[start:start + item['size']]
                assert len(payload) == item['size']
                target.write_bytes(payload)
    dest.mkdir(parents=True, exist_ok=True)
    walk(header['files'], dest)


def patch_main(source):
    anchor = "var userDataDir = app.getPath('userData')"
    assert source.count(anchor) == 1
    patch = """// Lazycat packaging: set paths BEFORE initializing the business store.
var persistentData = process.env.QUOTE_DATA_DIR
var persistentExports = process.env.QUOTE_EXPORT_DIR
if (!persistentData || !persistentExports) throw new Error('Use /usr/local/bin/start-quote')
fs.mkdirSync(persistentData, { recursive: true })
fs.mkdirSync(persistentExports, { recursive: true })
app.setPath('userData', persistentData)
app.setPath('documents', persistentExports)
app.setPath('downloads', persistentExports)
"""
    source = source.replace(anchor, patch + anchor)
    # A relative default filename would otherwise use a nonpersistent GTK location.
    old = "defaultPath: defaultName || 'quotation-backup.json'"
    assert source.count(old) == 1
    source = source.replace(old, "defaultPath: path.join(persistentExports, path.basename(defaultName || 'quotation-backup.json'))")
    old = 'defaultPath: defaultName,'
    assert source.count(old) == 1
    return source.replace(old, 'defaultPath: path.join(persistentExports, path.basename(defaultName)),')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('archive', type=pathlib.Path)
    args = p.parse_args()
    vendor = ROOT / 'images/vendor'
    vendor.mkdir(parents=True, exist_ok=True)
    runtime = vendor / f'electron-v{VERSION}-linux-x64.zip'
    if not runtime.exists():
        urllib.request.urlretrieve(f'{URL}/{runtime.name}', runtime)
    assert digest(runtime.read_bytes()) == RUNTIME_SHA256, 'Electron SHA256 mismatch'
    with zipfile.ZipFile(args.archive) as z:
        executable = z.read('linux-unpacked/quote-desktop')
        versions = set(re.findall(rb'Electron/([0-9.]+)', executable))
        assert versions == {VERSION.encode()}, f'Unexpected Electron version: {versions}'
        asar = z.read('linux-unpacked/resources/app.asar')
        icon = z.read('__appImage-x64/usr/share/icons/hicolor/0x0/apps/quote-desktop.png')
    (vendor / 'app.asar').write_bytes(asar)
    (ROOT / 'lzc-icon.png').write_bytes(icon)
    (ROOT / 'images/icon.png').write_bytes(icon)
    out = vendor / 'quote-desktop'
    # This directory contains generated files only; avoid stale files on rebuild.
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    with zipfile.ZipFile(runtime) as z:
        for entry in z.infolist():
            path = pathlib.PurePosixPath(entry.filename)
            assert not path.is_absolute() and '..' not in path.parts
        z.extractall(out)
    (out / 'electron').rename(out / 'quote-desktop')
    (out / 'resources/default_app.asar').unlink(missing_ok=True)
    app = out / 'resources/app'
    unpack_asar(asar, app)
    main_js = app / 'main.js'
    main_js.write_text(patch_main(main_js.read_text()), encoding='utf-8')
    for name in ('quote-desktop', 'chrome-sandbox', 'chrome_crashpad_handler'):
        (out / name).chmod(0o755)
    provenance = {
        'archive_sha256': digest(args.archive.read_bytes()),
        'original_asar_sha256': digest(asar),
        'electron_version': VERSION,
        'electron_url': f'{URL}/{runtime.name}',
        'electron_sha256': RUNTIME_SHA256,
        'patched_main_sha256': digest(main_js.read_bytes()),
        'base_image': 'kasmweb/core-debian-bookworm:1.17.0',
        'base_amd64_manifest': 'sha256:366a6a02c3d8dcba4fa492acbf8ad5cd71c8b85884532f8d767b49e39ffea1fe',
    }
    (ROOT / 'sources.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    main()
