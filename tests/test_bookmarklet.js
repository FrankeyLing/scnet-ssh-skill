const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');
const bookmark = fs.readFileSync(path.join(__dirname, '..', 'browser', 'selected-panel.bookmarklet.txt'), 'utf8').trim();
assert(bookmark.startsWith('javascript:'));

function run(location, selection) {
  const calls = [];
  const context = {
    location,
    window: {getSelection: () => selection},
    alert: message => calls.push(['alert', message]),
    prompt: (message, value) => calls.push(['prompt', value])
  };
  vm.runInNewContext(bookmark.slice('javascript:'.length), context, {timeout: 1000});
  return calls;
}
const allowed = {protocol: 'https:', hostname: 'www.scnet.cn', port: ''};
const sample = '主机\nexample.org\n端口号\n22\n用户名\ndemo';
assert.deepStrictEqual(run(allowed, sample), [['prompt', sample]]);
for (const location of [
  {protocol: 'http:', hostname: 'www.scnet.cn', port: ''},
  {protocol: 'https:', hostname: 'scnet.cn', port: ''},
  {protocol: 'https:', hostname: 'www.scnet.cn.evil.example', port: ''},
  {protocol: 'https:', hostname: 'www.scnet.cn', port: '8443'}
]) assert.strictEqual(run(location, sample)[0][0], 'alert');
assert.strictEqual(run(allowed, '')[0][0], 'alert');
assert.strictEqual(run(allowed, 'x'.repeat(8193))[0][0], 'alert');
console.log('Bookmarklet isolated tests passed');
