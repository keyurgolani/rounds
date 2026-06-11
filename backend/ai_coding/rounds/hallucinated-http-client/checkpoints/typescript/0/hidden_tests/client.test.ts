import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer, type Server } from 'node:http';

import { fetchUser, config } from '../../client.ts';

let server: Server;
let baseUrl: string;

before(async () => {
  server = createServer((req, res) => {
    if (req.url?.startsWith('/users/')) {
      const id = req.url.replace('/users/', '');
      res.statusCode = 200;
      res.setHeader('Content-Type', 'application/json');
      res.end(JSON.stringify({ id, name: 'Real' }));
    } else {
      res.statusCode = 404;
      res.end();
    }
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', () => resolve()));
  const addr = server.address();
  baseUrl =
    typeof addr === 'object' && addr ? `http://127.0.0.1:${addr.port}` : '';
  config.baseUrl = baseUrl;
});

after(async () => {
  await new Promise<void>((resolve) => server.close(() => resolve()));
});

test('fetchUser against real server', async () => {
  const result = await fetchUser('u-42');
  assert.deepEqual(result, { id: 'u-42', name: 'Real' });
});
