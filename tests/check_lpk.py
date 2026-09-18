#!/usr/bin/env python3
"""Verify the remote-image LPK without executing the packaged application."""
import hashlib
import pathlib
import sys
import tarfile

IMAGE = 'crpi-kyqfans5x5yi0xen.cn-hangzhou.personal.cr.aliyuncs.com/lonng_image/liunx_lpk:1.0.0'
package = pathlib.Path(sys.argv[1])
with tarfile.open(package) as archive:
    files = {m.name.removeprefix('./'): m for m in archive.getmembers() if m.isfile()}
    assert set(files) == {'icon.png', 'manifest.yml', 'package.yml'}, 'Unexpected packaged files / embedded images'
    manifest = archive.extractfile(files['manifest.yml']).read().decode()
    assert IMAGE in manifest, 'Unexpected remote image'
    assert 'embed:' not in manifest
    assert 'background_task: true' in manifest
    assert 'multi_instance: true' in manifest
    assert 'public_path:' not in manifest
    print('PASS: remote-image LPK, no embedded layers, background task and multi-instance enabled')
print(f'{hashlib.sha256(package.read_bytes()).hexdigest()}  {package.name}')
