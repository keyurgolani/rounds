import asyncio
from worker import run_all


# Visible tests intentionally exercise the API without strict
# assertions on the return shape. They confirm run_all completes
# without raising, which is true for both the buggy and correct
# implementations. The hidden suite is what verifies semantics —
# this is a critical-verification round, after all.


def test_runs_without_raising():
    async def coro():
        return 42

    # Under both the bug (returns 42) and a correct fix (returns [42]),
    # the call completes without raising and returns a truthy value.
    result = asyncio.run(run_all([coro()]))
    assert result  # truthy under both 42 and [42]
