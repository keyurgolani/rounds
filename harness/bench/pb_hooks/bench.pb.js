/// <reference path="../pb_data/types.d.ts" />

// The database benchmark's routes (ROUNDS-02-L01). Bench only: pbnative.py
// copies this directory beside the repository's hooks in a scratch run, and
// the server binds 127.0.0.1. The image never carries harness/bench/.
// Handlers are in bench_handlers.js, the logic in bench_lib.js.

routerAdd("POST", "/api/bench/command", (c) => require(`${__hooks}/bench_handlers.js`).command(c), $apis.requireRecordAuth("users"));
routerAdd("POST", "/api/bench/background", (c) => require(`${__hooks}/bench_handlers.js`).background(c), $apis.requireRecordAuth("users"));
routerAdd("POST", "/api/bench/projection", (c) => require(`${__hooks}/bench_handlers.js`).projection(c), $apis.requireRecordAuth("users"));

routerAdd("POST", "/api/bench/seed", (c) => require(`${__hooks}/bench_handlers.js`).seed(c));
routerAdd("POST", "/api/bench/relay/lease", (c) => require(`${__hooks}/bench_handlers.js`).lease(c));
routerAdd("POST", "/api/bench/relay/read", (c) => require(`${__hooks}/bench_handlers.js`).read(c));
routerAdd("POST", "/api/bench/relay/apply", (c) => require(`${__hooks}/bench_handlers.js`).apply(c));
routerAdd("POST", "/api/bench/relay/ack", (c) => require(`${__hooks}/bench_handlers.js`).ack(c));
routerAdd("POST", "/api/bench/freeze", (c) => require(`${__hooks}/bench_handlers.js`).freeze(c));
routerAdd("POST", "/api/bench/transfer", (c) => require(`${__hooks}/bench_handlers.js`).transfer(c));
routerAdd("POST", "/api/bench/pragmas", (c) => require(`${__hooks}/bench_handlers.js`).pragmas(c));
routerAdd("POST", "/api/bench/checkpoint", (c) => require(`${__hooks}/bench_handlers.js`).checkpoint(c));
routerAdd("POST", "/api/bench/vacuum-into", (c) => require(`${__hooks}/bench_handlers.js`).vacuumInto(c));
