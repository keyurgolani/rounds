// Bundles src/entry.mjs into dist/materialize.mjs (ROUNDS-00A-L04).
//
//   node backend/materializer/build.mjs
//
// Every React import, the frontend templates' JSX runtime included,
// resolves from this package's node_modules, so the bundle holds one React
// 18.3.1 even where frontend/node_modules exists. Paths in the output are
// relative to the repository root wherever the build runs, so a build of
// the same sources and lockfile gives the same bytes, and the same
// materializer_digest.

import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';

const here = fileURLToPath(new URL('.', import.meta.url));
const root = fileURLToPath(new URL('../../', import.meta.url));

const pinReact = {
  name: 'pin-react',
  setup(bundle) {
    bundle.onResolve({ filter: /^react(?:-dom)?(?:\/|$)/ }, (args) => {
      if (args.pluginData?.pinned) return undefined;
      return bundle.resolve(args.path, { kind: args.kind, resolveDir: here, pluginData: { pinned: true } });
    });
  },
};

await build({
  absWorkingDir: root,
  entryPoints: ['backend/materializer/src/entry.mjs'],
  outfile: 'backend/materializer/dist/materialize.mjs',
  plugins: [pinReact],
  bundle: true,
  platform: 'node',
  format: 'esm',
  target: 'node22',
  jsx: 'automatic',
  charset: 'utf8',
  define: { 'process.env.NODE_ENV': '"production"' },
  logLevel: 'warning',
});
