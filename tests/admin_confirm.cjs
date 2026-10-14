// Run with Node: node tests/admin_confirm.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../resources/js/admin_confirm.js'), 'utf8');
let handler;
let answer;
let messages = [];
const context = vm.createContext({
    document: { addEventListener(type, callback) {
        assert.equal(type, 'submit');
        handler = callback;
    } },
    window: { confirm(message) { messages.push(message); return answer; } },
    XSS_EXECUTED: false,
});
vm.runInContext(source, context);
const payloads = [
    "O'Connor & kelas 6",
    "'+(globalThis.XSS_EXECUTED=true)+'",
    '"><img src=x onerror="globalThis.XSS_EXECUTED=true">',
    '</script><script>globalThis.XSS_EXECUTED=true</script>',
];
for (const prefix of ['Hapus siswa ', 'Hapus guru ', 'Hapus kelas ', 'Generate ulang token untuk ']) {
    for (const name of payloads) {
        for (const accepted of [true, false]) {
            answer = accepted;
            messages = [];
            let prevented = false;
            const message = prefix + name + '?';
            handler({
                target: { matches: selector => selector === 'form[data-confirm]', dataset: { confirm: message } },
                preventDefault() { prevented = true; },
            });
            assert.deepEqual(messages, [message]);
            assert.equal(prevented, !accepted);
            assert.equal(context.XSS_EXECUTED, false);
        }
    }
}
messages = [];
handler({ target: { matches: () => false }, preventDefault() { assert.fail('Unrelated form blocked'); } });
assert.equal(messages.length, 0);
console.log('PASS: 32 confirmation cases; payloads remain text; OK/Cancel and unrelated forms preserved.');
