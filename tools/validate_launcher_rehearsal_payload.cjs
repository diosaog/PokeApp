// Prove disposable NSIS rehearsal uses the stable application's exact code.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const asar = require('../companion/launcher/node_modules/@electron/asar');
const [stable, rehearsal, output] = process.argv.slice(2);
assert(stable && rehearsal && output, 'stable rehearsal output required');
const archive = root => path.join(root, 'release/win-unpacked/resources/app.asar');
const files = file => asar.listPackage(file).map(n => n.replace(/^[\\/]/, ''))
  .filter(n => !asar.statFile(file, n).files).sort();
const a = archive(stable), b = archive(rehearsal);
assert.deepEqual(files(a), files(b));
for (const name of files(a).filter(n => n !== 'package.json'))
  assert(asar.extractFile(a, name).equals(asar.extractFile(b, name)), name);
const metadata = file => JSON.parse(asar.extractFile(file, 'package.json'));
const pa = metadata(a), pb = metadata(b);
assert.equal(pa.pokeappPrivateCandidate, false);
assert.equal(pb.pokeappVariant, 'updatetest');
for (const p of [pa, pb]) for (const key of ['pokeappPrivateCandidate', 'pokeappVariant', 'pokeappUpdate']) delete p[key];
assert.deepEqual(pa, pb);
function walk(root, sub = '') {
  return fs.readdirSync(path.join(root, sub), {withFileTypes: true}).flatMap(d =>
    d.isDirectory() ? walk(root, path.join(sub, d.name)) : [path.join(sub, d.name)]).sort();
}
const ar = path.join(stable, 'release/win-unpacked/resources/runtime');
const br = path.join(rehearsal, 'release/win-unpacked/resources/runtime');
const runtime = walk(ar);
assert.deepEqual(runtime, walk(br));
const hash = f => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
for (const name of runtime) assert.equal(hash(path.join(ar, name)), hash(path.join(br, name)), name);
const report = {status: 'PASS', version: pa.version, application_file_count: files(a).length - 1,
  runtime_file_count: runtime.length, application_files_identical: true, runtime_files_identical: true};
assert(!fs.existsSync(output), 'retained evidence must not be overwritten');
fs.writeFileSync(output, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report));
