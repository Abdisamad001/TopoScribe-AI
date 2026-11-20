
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');
const source = path.join(root, 'local', 'pt-api');
const target = path.join(root, 'src', 'app', 'api', 'pt');
const apiDir = path.join(root, 'src', 'app', 'api');

function rmDir(dir) {
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const from = path.join(src, entry.name);
    const to = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDir(from, to);
    } else if (entry.isFile() && entry.name !== 'README.md') {
      fs.copyFileSync(from, to);
    }
  }
}

function enable() {
  if (!fs.existsSync(source)) {
    console.error(`[pt-api] missing source: ${source}`);
    process.exit(1);
  }
  rmDir(target);
  copyDir(source, target);
  console.log('[pt-api] enabled → src/app/api/pt (local Packet Tracer proxy)');
}

function disable() {
  rmDir(target);
  // Clean empty parents so Next does not see a leftover api tree.
  if (fs.existsSync(apiDir)) {
    const leftover = fs.readdirSync(apiDir);
    if (leftover.length === 0) {
      rmDir(apiDir);
    }
  }
  // Drop stale Next typed-route stubs that still import /api/pt/* after removal.
  rmDir(path.join(root, '.next'));
  console.log('[pt-api] disabled — static export can emit out/');
}

const cmd = (process.argv[2] || '').trim();
if (cmd === 'enable') enable();
else if (cmd === 'disable') disable();
else {
  console.error('Usage: node scripts/pt-api.mjs <enable|disable>');
  process.exit(1);
}
