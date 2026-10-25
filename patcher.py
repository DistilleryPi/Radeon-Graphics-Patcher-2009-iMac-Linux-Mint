#!/usr/bin/env python3
"""Portable, fail-closed source patcher for the iMac10,1 Radeon panel experiment."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REL = Path('drivers/gpu/drm/radeon/radeon_connectors.c')
BACKUP = '.imac-radeon-original'
STATE = '.imac-radeon-state.json'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def patch(root, reverse=False, dry=True):
    args = ['patch', '--batch', '--fuzz=0', '--no-backup-if-mismatch', '-p1']
    args += ['--reverse', '--force'] if reverse else ['--forward']
    if dry:
        args += ['--dry-run']
    return subprocess.run(args + ['-i', str(HERE / 'panel.patch')], cwd=root,
                          capture_output=True, text=True)

def hardware():
    dmi = Path('/sys/class/dmi/id/product_name')
    model = dmi.read_text().strip() if dmi.exists() else 'unknown'
    devices = []
    for device in Path('/sys/bus/pci/devices').glob('*'):
        def value(name):
            return (device / name).read_text().strip()
        try:
            ids = [value(n) for n in ('vendor', 'device', 'subsystem_vendor', 'subsystem_device')]
            if ids[0] == '0x1002':
                devices.append({'address': device.name, 'ids': ids})
        except OSError:
            pass
    print(json.dumps({'model': model, 'amd_devices': devices,
        'target_present': model == 'iMac10,1' and any(d['ids'] ==
        ['0x1002', '0x9488', '0x106b', '0x00b6'] for d in devices)}, indent=2))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['detect', 'check', 'apply', 'undo'])
    parser.add_argument('source', nargs='?', type=Path, help='Linux source root (cross-builds supported)')
    args = parser.parse_args()
    if args.action == 'detect':
        hardware()
        return
    if args.source is None:
        parser.error('source root required')
    root = args.source.resolve()
    target = root / REL
    if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(root):
        raise RuntimeError('Expected a regular Radeon source file inside the source root')
    backup = target.with_name(target.name + BACKUP)
    state = target.with_name(target.name + STATE)
    if args.action == 'undo':
        info = json.loads(state.read_text())
        if digest(target.read_bytes()) != info['patched_sha256']:
            raise RuntimeError('Source changed after patching; refusing to overwrite edits')
        data = backup.read_bytes()
        if digest(data) != info['original_sha256']:
            raise RuntimeError('Backup checksum mismatch')
        target.write_bytes(data)
        state.unlink()
        backup.unlink()
        print('Original source restored')
        return
    reverse = patch(root, reverse=True)
    if reverse.returncode == 0:
        print('Patch already present; no changes made')
        return
    check = patch(root)
    if check.returncode:
        raise RuntimeError('Unsupported source layout; no changes made:\n' + check.stdout + check.stderr)
    if args.action == 'check':
        print('Compatible source; patch can be applied')
        return
    if backup.exists() or state.exists():
        raise RuntimeError('Existing backup/state requires review before patching')
    original = target.read_bytes()
    with backup.open('xb') as stream:
        stream.write(original)
    result = patch(root, dry=False)
    if result.returncode:
        target.write_bytes(original)
        backup.unlink()
        raise RuntimeError('Patch failed; original restored:\n' + result.stdout + result.stderr)
    state.write_text(json.dumps({'original_sha256': digest(original),
                                'patched_sha256': digest(target.read_bytes())}, indent=2) + '\n')
    print('Applied experimental panel quirk; original backed up. Rebuild your distro kernel to use it.')

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print('error: ' + str(error), file=sys.stderr)
        sys.exit(1)
