"""The execution-control protocol on the runner (ROUNDS-00A-L03).

PocketBase keeps every job, attempt, lease, and result envelope
(pocketbase/pb_hooks/execution.js); the runner keeps none:

- ``kinds``: the kinds, states, outcome classes, and wall budgets.
- ``envelope``: rounds.execution-envelope/v1 and how parts add up.
- ``executor``: the executor port and the legacy in-process adapter.
- ``store``: the client of the store's service routes.
- ``worker``: claim, heartbeat, complete, and reap.
- ``runtime``: starts the worker while ROUNDS_GATE_EXECUTION_STORE is on,
  and answers /ready.
"""
