"""Share link passwords (ROUNDS-00B-L04, app/share_password.py): the pw1
profile, the password bounds, one verify for every password sent, with a
dummy when there's nothing to verify against, and at most two
Argon2id runs at once in a process."""
from __future__ import annotations

import asyncio
import threading
import time

import argon2
import pytest

from app import share_password

PASSWORD = "correct horse battery"


def _run(coro):
    return asyncio.run(coro)


# ---- the profile and the bounds ---------------------------------------------


def test_a_verifier_is_pw1_argon2id_with_the_pinned_parameters():
    verifier = _run(share_password.hash_password(PASSWORD))
    assert verifier.startswith("pw1$argon2id$v=19$m=19456,t=2,p=1$")
    assert share_password.is_current(verifier)
    params = argon2.extract_parameters(verifier[len("pw1"):])
    assert (params.type, params.version, params.memory_cost, params.time_cost, params.parallelism) == (
        argon2.Type.ID, 19, 19456, 2, 1)
    assert (params.salt_len, params.hash_len) == (16, 32)
    # It fits the capability's password_policy_ref: printable, no space.
    assert len(verifier) <= 512 and all(33 <= ord(c) <= 126 for c in verifier)


def test_every_verifier_has_its_own_salt():
    a, b = (_run(share_password.hash_password(PASSWORD)) for _ in range(2))
    assert a != b


def test_a_verifier_never_holds_the_password():
    verifier = _run(share_password.hash_password(PASSWORD))
    assert PASSWORD not in verifier and PASSWORD.encode().hex() not in verifier


@pytest.mark.parametrize("length, ok", [(7, False), (8, True), (128, True), (129, False)])
def test_the_password_bounds(length, ok):
    value = "p" * length
    assert share_password.valid_password(value) is ok
    if ok:
        assert share_password.is_current(_run(share_password.hash_password(value)))
    else:
        with pytest.raises(ValueError):
            _run(share_password.hash_password(value))


@pytest.mark.parametrize("value", [None, 12345678, b"bytes-password", "\ud800abcdefgh"])
def test_only_text_that_encodes_as_utf8_is_a_password(value):
    assert not share_password.valid_password(value)


def test_bounds_count_characters_not_bytes():
    assert share_password.valid_password("é" * 128)
    assert share_password.valid_password("🔑" * 8)


@pytest.mark.parametrize(
    "verifier",
    [
        "",
        None,
        "$argon2id$v=19$m=19456,t=2,p=1$" + "A" * 22 + "$" + "A" * 43,
        "pw2$argon2id$v=19$m=19456,t=2,p=1$" + "A" * 22 + "$" + "A" * 43,
        "pw1$argon2id$v=19$m=4096,t=2,p=1$" + "A" * 22 + "$" + "A" * 43,
        "pw1$argon2id$v=19$m=19456,t=1,p=1$" + "A" * 22 + "$" + "A" * 43,
        "pw1$argon2id$v=19$m=19456,t=2,p=2$" + "A" * 22 + "$" + "A" * 43,
        "pw1$argon2i$v=19$m=19456,t=2,p=1$" + "A" * 22 + "$" + "A" * 43,
        "pw1$argon2id$v=16$m=19456,t=2,p=1$" + "A" * 22 + "$" + "A" * 43,
        "pw1$argon2id$v=19$m=19456,t=2,p=1$" + "A" * 11 + "$" + "A" * 43,
        "pw1$argon2id$v=19$m=19456,t=2,p=1$" + "A" * 22 + "$" + "A" * 22,
        "pw1$argon2id$v=19$m=19456,t=2,p=1$" + "A" * 22 + "$" + "A" * 43 + "\n",
    ],
    ids=["empty", "none", "no-profile", "other-profile", "less-memory", "fewer-passes", "more-lanes", "argon2i",
         "old-version", "short-salt", "short-hash", "trailing"],
)
def test_a_verifier_under_any_other_profile_is_not_current(verifier):
    assert not share_password.is_current(verifier)


# ---- verify -----------------------------------------------------------------


def test_the_right_password_verifies_and_a_wrong_one_does_not():
    verifier = _run(share_password.hash_password(PASSWORD))
    assert _run(share_password.verify(PASSWORD, verifier)) is True
    assert _run(share_password.verify(PASSWORD + "!", verifier)) is False
    assert _run(share_password.verify("", verifier)) is False


def test_another_profiles_verifier_never_resolves_even_with_its_password():
    # A real Argon2id verifier for the password, under weaker parameters.
    weak = "pw1" + argon2.PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PASSWORD)
    assert not share_password.is_current(weak)
    assert _run(share_password.verify(PASSWORD, weak)) is False


@pytest.fixture
def counted(monkeypatch):
    """Counts the Argon2id verifies, and which verifier each one used."""
    calls: list[str] = []

    class Counting:
        def __init__(self, inner):
            self.inner = inner

        def hash(self, password):
            return self.inner.hash(password)

        def verify(self, hash_, password):
            calls.append(hash_)
            return self.inner.verify(hash_, password)

    monkeypatch.setattr(share_password, "_hasher", Counting(share_password._hasher))
    return calls


@pytest.mark.parametrize(
    "case",
    ["unknown-link", "unprotected-link", "other-profile", "protected-wrong-password", "protected-right-password"],
)
def test_every_password_sent_costs_one_verify(counted, case):
    real = _run(share_password.hash_password(PASSWORD))
    share_password._dummy_verifier()  # made before counting, as warm() does at start
    verifier = {
        "unknown-link": None,
        "unprotected-link": "",
        "other-profile": "pw2" + real[3:],
        "protected-wrong-password": real,
        "protected-right-password": real,
    }[case]
    submitted = PASSWORD if case == "protected-right-password" else "not the password"
    ok = _run(share_password.verify(submitted, verifier))
    assert ok is (case == "protected-right-password")
    assert len(counted) == 1
    # Against the share's own verifier only when it's current; otherwise the dummy.
    expected = real[3:] if case.startswith("protected") else share_password._dummy_verifier()[3:]
    assert counted == [expected]


@pytest.mark.parametrize("password", [None, 42, "\ud800" * 9, "x" * 129, ""])
def test_a_password_that_could_never_match_still_costs_one_verify(counted, password):
    real = _run(share_password.hash_password(PASSWORD))
    assert _run(share_password.verify(password, real)) is False
    assert len(counted) == 1


def test_the_dummy_is_made_once_per_process_and_is_pw1():
    share_password._dummy = None
    _run(share_password.warm())
    first = share_password._dummy
    assert share_password.is_current(first)
    _run(share_password.verify("anything at all", None))
    assert share_password._dummy is first


def test_at_most_two_run_at_once(monkeypatch):
    running = 0
    most = 0
    lock = threading.Lock()

    def slow(password, verifier):
        nonlocal running, most
        with lock:
            running += 1
            most = max(most, running)
        time.sleep(0.05)
        with lock:
            running -= 1
        return False

    monkeypatch.setattr(share_password, "_verify", slow)

    async def many():
        await asyncio.gather(*(share_password.verify("p" * 8, None) for _ in range(8)))

    _run(many())
    assert most == share_password.CONCURRENCY == 2


def test_hashing_shares_the_same_two_slots(monkeypatch):
    running = 0
    most = 0
    lock = threading.Lock()

    def slow(*_args):
        nonlocal running, most
        with lock:
            running += 1
            most = max(most, running)
        time.sleep(0.05)
        with lock:
            running -= 1
        return "pw1"

    monkeypatch.setattr(share_password, "_verify", slow)
    monkeypatch.setattr(share_password, "_hash", slow)

    async def many():
        await asyncio.gather(*(share_password.verify("p" * 8, None) for _ in range(4)),
                             *(share_password.hash_password("p" * 8) for _ in range(4)))

    _run(many())
    assert most == 2


def test_the_work_runs_off_the_event_loop(monkeypatch):
    seen = []
    monkeypatch.setattr(share_password, "_verify", lambda *_a: seen.append(threading.current_thread()) or False)
    _run(share_password.verify("p" * 8, None))
    assert seen and seen[0] is not threading.main_thread()
