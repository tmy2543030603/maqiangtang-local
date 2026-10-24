const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = process.argv[2] || 'output/patched-source';
const front = fs.readFileSync(path.join(root, 'dist/assets/AjO5HB7j.js'), 'utf8');
const main = fs.readFileSync(path.join(root, 'dist-electron/electron/main.js'), 'utf8');
let reads = 0, requests = 0;
const context = vm.createContext({
  localStorage: { getItem() { reads++; return null; } },
  fetch() { requests++; throw Error('unexpected remote request'); },
  d: { useContext() { return { isVip: false, isChecking: true, isGreenDiamond: false }; } },
  Ye: {}, et: {},
});
function segment(source, start, end) {
  const a = source.indexOf(start);
  assert(a >= 0, start);
  const b = source.indexOf(end, a);
  assert(b > a, end);
  return source.slice(a, b);
}
vm.runInContext(segment(front, 'function X(){', 'async function G('), context);
vm.runInContext(segment(front, 'function Pe(e="Using cached VIP status"){', 'async function Ie('), context);
vm.runInContext(segment(main, 'async function isUserLoggedInForMainWindow(){', 'function hashMainWindowAuthToken('), context);
vm.runInContext('var useVip=' + segment(front, 'Ze=()=>{const e=d.useContext(Ye);', ',et=d.createContext').slice(3) + ';', context);
vm.runInContext('var useGreen=' + segment(front, 'tt=()=>({...d.useContext(et)', ',nt=').slice(3) + ';', context);
(async () => {
  assert.equal(vm.runInContext('H()', context), true);
  assert.equal(vm.runInContext('W()', context), null);
  assert.equal(vm.runInContext('X().username', context), '本地离线模式');
  assert.equal(vm.runInContext('X().isVip', context), true);
  assert.equal((await vm.runInContext('ze()', context)).loggedIn, true);
  assert.equal((await vm.runInContext('Me()', context)).isVip, true);
  assert.equal(vm.runInContext('useVip().isVip', context), true);
  assert.equal(vm.runInContext('useVip().isChecking', context), false);
  assert.equal(vm.runInContext('useGreen().isGreenDiamond', context), true);
  assert.equal(await vm.runInContext('isUserLoggedInForMainWindow()', context), true);
  assert.equal(await vm.runInContext('isUserVipForMainWindow()', context), true);
  assert.equal(reads, 0);
  assert.equal(requests, 0);
  console.log('PASS: 13 behavioral assertions; no credentials or remote requests needed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
