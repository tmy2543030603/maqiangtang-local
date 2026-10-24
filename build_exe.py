"""Build the standalone Windows GUI executable."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
subprocess.run([
    sys.executable, '-m', 'PyInstaller',
    '--noconfirm', '--clean', '--onefile', '--windowed',
    '--name', 'MaQiangTang-Local-Builder',
    '--distpath', str(root / 'dist'),
    '--workpath', str(root / 'build' / 'work'),
    '--specpath', str(root / 'build'),
    str(root / 'launcher.py'),
], cwd=root, check=True)
print(root / 'dist' / 'MaQiangTang-Local-Builder.exe')
