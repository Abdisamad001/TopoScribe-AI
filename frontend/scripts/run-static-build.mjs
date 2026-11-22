/**
 * Cloudflare/static build: force Next output: 'export' via env, then next build.
 * Local `npm run dev` leaves NEXT_OUTPUT_EXPORT unset so /api/pt/* works.
 */
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const env = { ...process.env, NEXT_OUTPUT_EXPORT: '1' };
const result = spawnSync('npx', ['next', 'build'], {
  cwd: root,
  env,
  stdio: 'inherit',
  shell: true,
});
process.exit(result.status ?? 1);
