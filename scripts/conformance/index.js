'use strict';
// Entry point for `node --test scripts/conformance`. Node 22 resolves a
// directory argument to its index.js, so this file loads every test module
// under test/. A module that fails to load fails the run.

const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const dir = path.join(__dirname, 'test');
for (const file of fs.readdirSync(dir).filter((f) => f.endsWith('.test.mjs')).sort()) {
  import(pathToFileURL(path.join(dir, file)).href).catch((err) => {
    console.error(`failed to load ${file}:`, err);
    process.exitCode = 1;
  });
}
