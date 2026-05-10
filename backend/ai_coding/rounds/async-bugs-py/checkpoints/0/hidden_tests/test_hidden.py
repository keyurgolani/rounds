import asyncio
import time
from worker import run_all


def test_returns_list_of_all_results():
    async def coro(n):
        await asyncio.sleep(0)
        return n * 10

    out = asyncio.run(run_all([coro(1), coro(2), coro(3)]))
    assert out == [10, 20, 30], f"expected list of all results, got {out!r}"


def test_runs_concurrently():
    async def coro(d):
        await asyncio.sleep(d)
        return d

    start = time.monotonic()
    out = asyncio.run(run_all([coro(0.1), coro(0.1), coro(0.1)]))
    elapsed = time.monotonic() - start
    assert out == [0.1, 0.1, 0.1]
    assert elapsed < 0.25, f"expected concurrent (~0.1s), took {elapsed:.3f}s"
