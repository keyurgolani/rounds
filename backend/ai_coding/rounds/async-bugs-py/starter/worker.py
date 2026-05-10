"""Async worker.

Spec:
  - run_all(coros) takes a list of coroutines and returns a list of
    their results in order.
  - All coroutines run concurrently — total wall time should be ~max
    of the individual durations, not the sum.

Implementation below was AI-generated. Visible tests verify the basic
shape; submission grades probe deeper invariants.
"""
import asyncio


async def run_all(coros):
    results = await asyncio.gather(*coros)
    return results[0]
