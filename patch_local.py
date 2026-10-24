"""Build a local-only patch for MaQiangTang 7.4.6 from a local installation."""
import argparse
import hashlib
import json
import shutil
import struct
from pathlib import Path

SUPPORTED_ASAR = '9546f4df4ba52ab46cf841792c5c66da9dc514e63d4b441d2ad9f8825421e230'
SUPPORTED_EXE = 'ab3155f4d8fb9e218ab4296eefb9b99656095f83c3eff61643d1552250537f4b'
FRONT = 'dist/assets/AjO5HB7j.js'
MAIN = 'dist-electron/electron/main.js'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def entry(header, path):
    node = header
    for part in path.split('/'):
        node = node['files'][part]
    return node


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Unexpected patch location: {old!r}')
    return text.replace(old, new, 1)


def inject(text, signature, body):
    return replace_once(text, signature, signature + body)


def patch_sources(front, main):
    user = json.dumps({
        'id': 'local-offline', 'username': '本地离线模式',
        'status': 'active', 'isVip': True, 'vipLevel': 1,
        'vipExpireAt': '2099-12-31T23:59:59.000Z',
        'isGreenDiamond': True,
        'greenDiamondExpireAt': '2099-12-31T23:59:59.000Z',
        'freezeUntil': None,
    }, ensure_ascii=True, separators=(',', ':'))
    front = inject(front, 'function X(){', 'return ' + user + ';')
    front = inject(front, 'function H(){', 'return true;')
    # Do not fabricate or send bearer tokens to remote account services.
    front = inject(front, 'function W(){', 'return null;')
    front = inject(front, 'function Pe(e="Using cached VIP status"){',
                   'return {success:true,isVip:true,vipExpireAt:"2099-12-31T23:59:59.000Z",daysRemaining:26000,expired:false,activatedAt:null,activatedCardKey:null,message:"Local offline mode"};')
    front = inject(front, 'async function Me(){', 'return Pe();')
    front = inject(front, 'async function ze(){',
                   'return {success:true,loggedIn:true,user:X(),message:"Local offline mode"};')
    front = replace_once(front,
        'return e},et=d.createContext({isGreenDiamond:!1',
        'return {...e,isVip:true,isChecking:false,refreshVipStatus:async()=>true}},et=d.createContext({isGreenDiamond:!1')
    front = replace_once(front, 'tt=()=>d.useContext(et),nt=',
        'tt=()=>({...d.useContext(et),isGreenDiamond:true,isChecking:false,greenDiamondExpireAt:"2099-12-31T23:59:59.000Z",daysRemaining:26000,refreshGreenDiamondStatus:async()=>true}),nt=')
    for name in ('isUserLoggedInForMainWindow', 'isUserVipForMainWindow'):
        main = inject(main, 'async function ' + name + '(){', 'return true;')
    return {FRONT: front.encode('utf8'), MAIN: main.encode('utf8')}


def build(install, output, portable=False):
    install, output = install.resolve(), output.resolve()
    if output.exists():
        raise ValueError('Output directory already exists; choose a new directory.')
    if output == install or install in output.parents or output in install.parents:
        raise ValueError('Output must be separate from the installation directory.')
    original = (install / 'resources/app.asar').read_bytes()
    executable = (install / '码枪堂.exe').read_bytes()
    if sha(original) != SUPPORTED_ASAR or sha(executable) != SUPPORTED_EXE:
        raise ValueError('Only the verified 7.4.6 build is supported; input hashes differ.')
    _, header_size, _, json_size = struct.unpack('<4I', original[:16])
    old_header = original[16:16 + json_size]
    header = json.loads(old_header)
    old_base = 8 + header_size
    payload = original[old_base:]
    def source(path):
        node = entry(header, path)
        start = old_base + int(node['offset'])
        return original[start:start + node['size']].decode('utf8')
    patches = patch_sources(source(FRONT), source(MAIN))
    for path, content in patches.items():
        node = entry(header, path)
        node['offset'], node['size'] = str(len(payload)), len(content)
        if 'integrity' in node:
            block = node['integrity'].get('blockSize', 4194304)
            node['integrity'] = {
                'algorithm': 'SHA256', 'hash': sha(content), 'blockSize': block,
                'blocks': [sha(content[i:i + block]) for i in range(0, len(content), block)],
            }
        payload += content
    new_header = json.dumps(header, ensure_ascii=False, separators=(',', ':')).encode('utf8')
    header_payload = struct.pack('<I', len(new_header)) + new_header + b'\0' * (-len(new_header) % 4)
    header_pickle = struct.pack('<I', len(header_payload)) + header_payload
    archive = struct.pack('<II', 4, len(header_pickle)) + header_pickle + payload
    old_hash, new_hash = sha(old_header).encode('ascii'), sha(new_header).encode('ascii')
    if executable.count(old_hash) != 1:
        raise ValueError('Expected one embedded ASAR header hash.')
    patched_exe = executable.replace(old_hash, new_hash, 1)
    new_base = 8 + len(header_pickle)
    for path, content in patches.items():
        node = entry(header, path)
        start = new_base + int(node['offset'])
        if archive[start:start + node['size']] != content:
            raise ValueError('Archive validation failed: ' + path)
    output.mkdir(parents=True)
    (output / 'app.local.asar').write_bytes(archive)
    (output / '码枪堂.local.exe').write_bytes(patched_exe)
    for path, content in patches.items():
        target = output / 'patched-source' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    report = {
        'version': '7.4.6', 'source_sha256': sha(original),
        'source_exe_sha256': sha(executable), 'patched_sha256': sha(archive),
        'patched_exe_sha256': sha(patched_exe), 'changed_files': list(patches),
        'scope': 'Local interface and overlay checks; remote accounts are not unlocked.',
    }
    if portable:
        target = output / 'portable'
        shutil.copytree(install, target)
        (target / 'resources/app.asar').write_bytes(archive)
        (target / '码枪堂.exe').write_bytes(patched_exe)
        report['portable'] = str(target)
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(report, ensure_ascii=True, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', type=Path, required=True, help='Local installation directory')
    parser.add_argument('--output', type=Path, default=Path('output'), help='New output directory')
    parser.add_argument('--portable', action='store_true', help='Also create a complete local application copy')
    args = parser.parse_args()
    build(args.install, args.output, args.portable)


if __name__ == '__main__':
    main()
