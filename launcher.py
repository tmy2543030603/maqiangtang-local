"""Double-click GUI and automation entry point for the standalone Windows tool."""
import argparse
import contextlib
import datetime
import io
import json
import os
import queue
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from patch_local import build


def write_report(path, data):
    if path:
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')


def run_gui(self_test=False):
    root = tk.Tk()
    root.title('码枪堂 7.4.6 · 本地模式生成器')
    root.geometry('720x430')
    root.minsize(660, 430)
    root.columnconfigure(0, weight=1)
    frame = ttk.Frame(root, padding=24)
    frame.grid(sticky='nsew')
    frame.columnconfigure(0, weight=1)
    ttk.Label(frame, text='生成独立本地版', font=('Microsoft YaHei UI', 17, 'bold')).grid(row=0, column=0, columnspan=2, sticky='w')
    ttk.Label(frame, text='选择已安装的 7.4.6 版本，生成到新文件夹；原安装保持原样。').grid(row=1, column=0, columnspan=2, sticky='w', pady=(8, 18))
    install = tk.StringVar(value=str(Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Stevenma' / 'MaQiangTang'))
    base = Path.home() / 'Desktop'
    if not base.is_dir():
        base = Path.home()
    def new_output(parent):
        return str(Path(parent) / ('码枪堂-本地版-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')))
    output = tk.StringVar(value=new_output(base))
    ttk.Label(frame, text='软件安装目录').grid(row=2, column=0, sticky='w')
    install_entry = ttk.Entry(frame, textvariable=install)
    install_entry.grid(row=3, column=0, sticky='ew', pady=(4, 12))
    def choose_install():
        selected = filedialog.askdirectory(title='选择包含码枪堂.exe的安装目录', initialdir=install.get(), parent=root)
        if selected:
            install.set(selected)
    install_button = ttk.Button(frame, text='浏览…', command=choose_install)
    install_button.grid(row=3, column=1, padx=(10, 0), pady=(4, 12))
    ttk.Label(frame, text='输出文件夹（自动新建）').grid(row=4, column=0, sticky='w')
    output_entry = ttk.Entry(frame, textvariable=output)
    output_entry.grid(row=5, column=0, sticky='ew', pady=(4, 12))
    def choose_output():
        selected = filedialog.askdirectory(title='选择保存位置', initialdir=str(base), parent=root)
        if selected:
            output.set(new_output(selected))
    output_button = ttk.Button(frame, text='浏览…', command=choose_output)
    output_button.grid(row=5, column=1, padx=(10, 0), pady=(4, 12))
    ttk.Label(frame, text='适用于本地功能；云端账户和服务器验证功能不在生成范围内。', foreground='#666666').grid(row=6, column=0, columnspan=2, sticky='w')
    status = tk.StringVar(value='就绪')
    ttk.Label(frame, textvariable=status).grid(row=7, column=0, columnspan=2, sticky='w', pady=(16, 5))
    progress = ttk.Progressbar(frame, mode='indeterminate')
    progress.grid(row=8, column=0, columnspan=2, sticky='ew')
    events = queue.Queue()
    state = {'busy': False, 'result': None}
    buttons = ttk.Frame(frame)
    buttons.grid(row=9, column=0, columnspan=2, sticky='e', pady=(14, 0))
    def open_folder():
        if state['result']:
            os.startfile(str(state['result']))
    open_button = ttk.Button(buttons, text='打开生成目录', command=open_folder, state='disabled')
    open_button.pack(side='left', padx=(0, 10))
    controls = [install_entry, output_entry, install_button, output_button]
    def start():
        source, target = Path(install.get().strip()), Path(output.get().strip())
        if not (source / '码枪堂.exe').is_file() or not (source / 'resources/app.asar').is_file():
            messagebox.showerror('安装目录不正确', '请选择同时包含码枪堂.exe与resources文件夹的目录。', parent=root)
            return
        if target.exists():
            messagebox.showerror('输出目录已存在', '请选择一个尚不存在的新文件夹，避免覆盖已有文件。', parent=root)
            return
        state['busy'] = True
        state['result'] = None
        for widget in controls + [start_button, open_button]:
            widget.configure(state='disabled')
        status.set('正在校验版本并生成副本，请稍候…')
        progress.start(15)
        def worker():
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    build(source, target, portable=True)
                events.put(('ok', target.resolve() / 'portable'))
            except Exception as error:
                events.put(('error', str(error)))
        threading.Thread(target=worker, daemon=True).start()
    start_button = ttk.Button(buttons, text='生成本地版', command=start)
    start_button.pack(side='left')
    def poll():
        try:
            kind, value = events.get_nowait()
        except queue.Empty:
            root.after(100, poll)
            return
        state['busy'] = False
        progress.stop()
        for widget in controls + [start_button]:
            widget.configure(state='normal')
        if kind == 'ok':
            state['result'] = value
            open_button.configure(state='normal')
            status.set('生成完成：点击“打开生成目录”后运行码枪堂.exe。')
            messagebox.showinfo('生成完成', '本地副本已生成：\n' + str(value) + '\n\n在此目录中运行码枪堂.exe。', parent=root)
        else:
            status.set('生成失败；原安装未修改。')
            messagebox.showerror('生成失败', value, parent=root)
        root.after(100, poll)
    def close():
        if state['busy']:
            messagebox.showinfo('正在生成', '请等待生成完成后再关闭窗口。', parent=root)
        else:
            root.destroy()
    root.protocol('WM_DELETE_WINDOW', close)
    root.after(100, poll)
    if self_test:
        try:
            root.update_idletasks()
            if frame.winfo_reqheight() > root.winfo_height():
                raise RuntimeError('GUI content exceeds the startup window height')
        finally:
            root.destroy()
    else:
        root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--install', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--report-file', type=Path)
    args = parser.parse_args()
    try:
        if args.self_test:
            run_gui(self_test=True)
            write_report(args.report_file, {'success': True, 'gui_initialized': True, 'gui_layout_verified': True, 'frozen': bool(getattr(sys, 'frozen', False))})
        elif args.install is not None:
            if args.output is None:
                raise ValueError('--output is required with --install')
            with contextlib.redirect_stdout(io.StringIO()):
                build(args.install, args.output, portable=True)
            write_report(args.report_file, {'success': True, 'portable': str(args.output.resolve() / 'portable')})
        else:
            run_gui()
        return 0
    except Exception as error:
        write_report(args.report_file, {'success': False, 'error': str(error)})
        if args.report_file is None:
            messagebox.showerror('本地模式生成器', str(error))
        return 1


if __name__ == '__main__':
    sys.exit(main())
