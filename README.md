# 码枪堂 7.4.6 本地模式工具

从本机安装文件生成独立副本，放开本地界面和悬浮窗中的登录、VIP、绿钻判断。工具不会写入原安装目录，也不会生成或提交远程账户凭据。

**适用范围仅为本地功能。** 云端收藏、发布、账户资料和需要服务器验证的下载没有解锁。界面的本地会员状态不代表远程账户取得会员。

## 直接使用 EXE

从 [Releases](https://github.com/tmy2543030603/maqiangtang-local/releases/latest) 下载 `MaQiangTang-Local-Builder.exe`。Windows x64 下可直接双击，无需安装 Python 或 Node.js。

1. 选择已经安装的码枪堂 7.4.6 目录。
2. 选择输出位置，点击“生成本地版”。
3. 完成后点击“打开生成目录”，运行其中的 `码枪堂.exe`。

输出保存在新文件夹中，原安装不变。这个 EXE 是本地副本生成器，不包含软件本体。

## 从源码运行

- Windows，Python 3.10 或更新版本，仅使用标准库。
- 本机已安装的码枪堂 7.4.6，且文件哈希符合下表。
- Node.js 22 或更新版本，用于可选验证。

| 输入文件 | SHA-256 |
| --- | --- |
| 原版归档 | `9546f4df4ba52ab46cf841792c5c66da9dc514e63d4b441d2ad9f8825421e230` |
| 原版主程序 | `ab3155f4d8fb9e218ab4296eefb9b99656095f83c3eff61643d1552250537f4b` |

版本号相同但哈希不同也会停止，避免误改其他构建。

## 生成独立副本

在仓库目录执行：

```powershell
python patch_local.py --install "C:\Program Files\Stevenma\MaQiangTang" --output output --portable
```

完成后运行 `output\portable\码枪堂.exe`。输出目录必须尚不存在，且不能与原安装目录相互包含。

不需要完整副本时，去掉 `--portable`。工具仍会生成修改后的主程序、归档、两份修改脚本和校验报告，全部放在输出目录中。

工具仅在两份应用脚本中插入本地返回逻辑，并更新对应文件的归档完整性信息和主程序内嵌的归档头 SHA-256。Electron 的归档完整性检查仍保留。修改主程序会使其原有代码签名失效（如果原程序带有签名）。

## 验证

生成文件后执行：

```powershell
node --check output/patched-source/dist/assets/AjO5HB7j.js
node --check output/patched-source/dist-electron/electron/main.js
node verify_local.cjs output/patched-source
```

行为脚本检查 13 项断言，包括无登录凭据时的本地身份、会员状态、悬浮窗判断，以及相关验证路径不发送网络请求。

这些检查不等于完整 GUI 或系统优化功能测试。驱动、色彩配置、系统设置等实际操作尚未逐项实测。程序启动仍可能需要 Windows 管理员权限；此工具不处理操作系统权限。

## 自行打包 EXE

在 Windows 上执行：

```powershell
python -m pip install -r requirements-build.txt
python build_exe.py
```

生成文件为 `dist\MaQiangTang-Local-Builder.exe`。仓库的 GitHub Actions 也会在相关源码更新时自动构建、验证 GUI 初始化，并上传到 Releases，附 SHA-256 校验文件。

## 文件范围与恢复

仓库仅包含工具源码和说明，不包含软件本体、提取后的厂商源码、安装包、备份、签名密钥或账户数据。`.gitignore` 已排除生成目录及常见二进制文件。

原安装保持原样。需要恢复时退出独立副本，重新使用原安装即可。应用升级会替换相关程序文件，此修改不保证适用于其他版本。
