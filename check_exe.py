import json, os, subprocess, pathlib
root=pathlib.Path(__file__).resolve().parent
exe=root/'dist/MaQiangTang-Local-Builder.exe'
report=root/'dist/self-test.json'
temp=root/'build/smoke-temp'
temp.mkdir(parents=True,exist_ok=True)
environment=dict(os.environ,TEMP=str(temp),TMP=str(temp))
print('Starting packaged GUI self-test',flush=True)
result=subprocess.run([str(exe),'--self-test','--report-file',str(report)],cwd=root,env=environment,timeout=60)
print('Exit code:',result.returncode,flush=True)
if result.returncode:
 raise SystemExit(result.returncode)
if not report.is_file():
 raise SystemExit('Packaged executable did not produce its verification report')
data=json.loads(report.read_text(encoding='utf8'))
assert data['success'] and data['gui_initialized'] and data['frozen'],data
print('PASS packaged GUI',flush=True)
