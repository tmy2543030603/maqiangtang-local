"""Build a portable (green, no-install) copy of MaQiangTang 7.4.6.

Applies three local modifications to a local installation, then writes a
complete application folder plus a ZIP:

* local-only login / VIP / green-diamond state;
* no automatic update poll on startup;
* the update dialog can never become a blocking forced update.

The original installation is never touched.
"""
import argparse
import hashlib
import json
import shutil
import struct
import zipfile
from pathlib import Path

SUPPORTED_ASAR = '9546f4df4ba52ab46cf841792c5c66da9dc514e63d4b441d2ad9f8825421e230'
SUPPORTED_EXE = 'ab3155f4d8fb9e218ab4296eefb9b99656095f83c3eff61643d1552250537f4b'
FRONT = 'dist/assets/AjO5HB7j.js'
MAIN = 'dist-electron/electron/main.js'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inject(text, signature, body, label):
    if text.count(signature) != 1:
        raise SystemExit(f'Unexpected patch point ({label}: {text.count(signature)} matches)')
    return text.replace(signature, signature + body, 1)


def replace_once(text, old, new, label):
    if text.count(old) != 1:
        raise SystemExit(f'Unexpected patch point ({label}: {text.count(old)} matches)')
    return text.replace(old, new, 1)


def patch_auth(front, main):
    user = json.dumps({
        'id': 'local-offline', 'username': '本地离线模式',
        'status': 'active', 'isVip': True, 'vipLevel': 1,
        'vipExpireAt': '2099-12-31T23:59:59.000Z',
        'isGreenDiamond': True,
        'greenDiamondExpireAt': '2099-12-31T23:59:59.000Z',
        'freezeUntil': None,
    }, ensure_ascii=True, separators=(',', ':'))
    front = inject(front, 'function X(){', 'return ' + user + ';', 'identity')
    front = inject(front, 'function H(){', 'return true;', 'login state')
    front = inject(front, 'function W(){', 'return null;', 'token')
    front = inject(front, 'function Pe(e="Using cached VIP status"){',
                   'return {success:true,isVip:true,vipExpireAt:"2099-12-31T23:59:59.000Z",daysRemaining:26000,expired:false,activatedAt:null,activatedCardKey:null,message:"Local offline mode"};',
                   'entitlement')
    front = inject(front, 'async function Me(){', 'return Pe();', 'entitlement refresh')
    front = inject(front, 'async function ze(){',
                   'return {success:true,loggedIn:true,user:X(),message:"Local offline mode"};', 'session')
    front = replace_once(
        front, 'return e},et=d.createContext({isGreenDiamond:!1',
        'return {...e,isVip:true,isChecking:false,refreshVipStatus:async()=>true}},et=d.createContext({isGreenDiamond:!1',
        'vip hook')
    front = replace_once(
        front, 'tt=()=>d.useContext(et),nt=',
        'tt=()=>({...d.useContext(et),isGreenDiamond:true,isChecking:false,greenDiamondExpireAt:"2099-12-31T23:59:59.000Z",daysRemaining:26000,refreshGreenDiamondStatus:async()=>true}),nt=',
        'audio hook')
    for name in ('isUserLoggedInForMainWindow', 'isUserVipForMainWindow'):
        main = inject(main, 'async function ' + name + '(){', 'return true;', name)
    return front, main


def patch_update(front):
    front = replace_once(front, 'setTimeout(tt,5e3)', '0', 'startup update poll')
    front = replace_once(front, 'const e=!0===r.forceUpdate', 'const e=!1', 'force update flag')
    return front


def build(install, output):
    install, output = install.resolve(), output.resolve()
    original = (install / 'resources/app.asar').read_bytes()
    executable = (install / '码枪堂.exe').read_bytes()
    if sha(original) != SUPPORTED_ASAR or sha(executable) != SUPPORTED_EXE:
        raise SystemExit('Only the verified 7.4.6 build is supported; input hashes differ.')

    _, header_size, _, json_size = struct.unpack('<4I', original[:16])
    old_header = original[16:16 + json_size]
    header = json.loads(old_header)
    old_base = 8 + header_size
    payload = original[old_base:]

    def entry(path):
        node = header
        for part in path.split('/'):
            node = node['files'][part]
        return node

    def read_entry(path):
        node = entry(path)
        start = old_base + int(node['offset'])
        return original[start:start + node['size']].decode('utf8')

    front, mainjs = patch_auth(read_entry(FRONT), read_entry(MAIN))
    front = patch_update(front)

    patches = {FRONT: front.encode('utf8'), MAIN: mainjs.encode('utf8')}
    for path, content in patches.items():
        node = entry(path)
        node['offset'] = str(len(payload))
        node['size'] = len(content)
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

    old_hash = sha(old_header).encode('ascii')
    new_hash = sha(new_header).encode('ascii')
    if executable.count(old_hash) != 1:
        raise SystemExit('Expected exactly one embedded archive hash.')
    patched_exe = executable.replace(old_hash, new_hash, 1)

    folder = output / 'MaQiangTang-Portable-7.4.6'
    zip_path = output / 'MaQiangTang-Portable-7.4.6.zip'
    if folder.exists():
        shutil.rmtree(folder)
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(install, folder)
    (folder / 'resources/app.asar').write_bytes(archive)
    (folder / '码枪堂.exe').write_bytes(patched_exe)
    for junk in ('Uninstall 码枪堂.exe',):
        target = folder / junk
        if target.exists():
            target.unlink()

    readme = '''码枪堂 7.4.6 免安装版（已移除强制更新）

使用方法：
1. 把整个压缩包解压到普通文件夹，例如 D:\\MaQiangTangPortable。
2. 双击文件夹里的“码枪堂.exe”直接使用。
3. 不要只复制 EXE，需保留 resources、locales 和全部 DLL。

本版本改动：
- 取消启动时自动检查更新，不再弹出“必须更新”拦截窗口。
- 即使手动点击“检查更新”，提示也可直接关闭，不会强制升级。
- 保留本地登录、会员、绿钻的本地判断。

说明：
- 云端账户、收藏、发布等需要服务器验证的功能不受此修改影响。
- 系统设置、驱动、色彩相关功能可能仍需要管理员权限。
- 如需更新软件，请自行前往官网下载新版；更新会覆盖本修改。
'''
    (folder / '使用说明.txt').write_text(readme, encoding='utf-8-sig')

    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for file in sorted(folder.rglob('*')):
            if file.is_file():
                z.write(file, 'MaQiangTang-Portable-7.4.6/' + file.relative_to(folder).as_posix())

    report = {
        'source_archive_sha256': sha(original),
        'patched_archive_sha256': sha(archive),
        'source_exe_sha256': sha(executable),
        'patched_exe_sha256': sha(patched_exe),
        'folder': str(folder),
        'zip': str(zip_path),
        'zip_sha256': sha(zip_path.read_bytes()),
        'zip_size': zip_path.stat().st_size,
    }
    (output / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(report, ensure_ascii=True, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', type=Path,
                        default=Path(r'C:\Program Files\Stevenma\MaQiangTang'))
    parser.add_argument('--output', type=Path, default=Path('release'))
    args = parser.parse_args()
    build(args.install, args.output)


if __name__ == '__main__':
    main()
