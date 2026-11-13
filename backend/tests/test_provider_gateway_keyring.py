"""The keyring (ROUNDS-14-L02, app/provider_gateway/keyring.py): the root
and when it counts, the keys it derives, the wraps of saved provider keys,
and the startup line."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import pathlib
import re
import secrets

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app import legacy_receipt, obs, share_secrets
from app.provider_gateway import keyring

SECRET = "test-keyring-secret-placeholder-0123456789"
ACCOUNT = "acct00000000001"
PROVIDER = "prov00000000001"
BINDING = keyring.Binding(ACCOUNT, PROVIDER, "api.example.test", 443)
KEY = "test-provider-key-placeholder"
BACKEND = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setenv("AI_KEY_SECRET", SECRET)
    monkeypatch.delenv("ROUNDS_ALLOW_DEV_KEY", raising=False)
    obs.reset_pseudonym_key()
    yield
    obs.reset_pseudonym_key()


def _hkdf(label: bytes, root: str = SECRET) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=label).derive(root.encode("utf-8"))


# ---- labels and derived keys ------------------------------------------------


def test_the_labels_are_pinned_byte_for_byte():
    assert keyring.LABELS == (
        b"rounds/share-digest/v1",
        b"rounds/share-throttle/v1",
        b"rounds/legacy-share-receipt/v1",
        b"rounds/legacy-snapshot-scan/v1",
        b"rounds/obs/account-pseudonym/v1",
        b"rounds/credential-wrap/v1",
    )
    assert keyring.ROOT_VERSION == 1


def test_every_existing_caller_uses_its_keyring_label():
    assert share_secrets.DIGEST_INFO is keyring.SHARE_DIGEST
    assert share_secrets.THROTTLE_INFO is keyring.SHARE_THROTTLE
    assert share_secrets.LEGACY_RECEIPT_INFO is keyring.LEGACY_SHARE_RECEIPT
    assert obs._PSEUDONYM_INFO is keyring.OBS_PSEUDONYM
    assert legacy_receipt.LABELS == {
        "legacy-snapshot-scan/v1": keyring.LEGACY_SNAPSHOT_SCAN.decode("ascii"),
        "legacy-share-receipt/v1": keyring.LEGACY_SHARE_RECEIPT.decode("ascii"),
    }


@pytest.mark.parametrize("label", keyring.LABELS)
def test_derive_is_hkdf_sha256_over_the_root_with_the_label(label):
    assert keyring.derive(label) == _hkdf(label)


def test_the_keys_already_in_use_keep_their_values():
    # Share digests, signed receipts and log pseudonyms made before the
    # keyring still match.
    assert share_secrets._derive(share_secrets.DIGEST_INFO) == _hkdf(b"rounds/share-digest/v1")
    assert share_secrets._derive(share_secrets.THROTTLE_INFO) == _hkdf(b"rounds/share-throttle/v1")
    for label in legacy_receipt.LABELS.values():
        assert legacy_receipt.key_for(label, SECRET) == _hkdf(label.encode("ascii"))
    assert obs._pseudonym_key() == _hkdf(b"rounds/obs/account-pseudonym/v1")


def test_every_derived_key_is_separate_from_the_others_and_the_legacy_wrap_key():
    keys = [keyring.derive(label) for label in keyring.LABELS]
    keys.append(hashlib.sha256(SECRET.encode("utf-8")).digest())
    assert len(set(keys)) == len(keys)


@pytest.mark.parametrize("label", [b"rounds/other/v1", b"", "rounds/share-digest/v1", b"rounds/share-digest/v2"])
def test_derive_refuses_a_label_it_doesnt_list(label):
    with pytest.raises(ValueError):
        keyring.derive(label)


def test_the_keyring_is_the_only_place_that_runs_hkdf():
    found = []
    for path in sorted(BACKEND.rglob("*.py")):
        rel = path.relative_to(BACKEND).as_posix()
        if rel.startswith(("tests/", "app/contracts/")) or rel == "app/provider_gateway/keyring.py":
            continue
        if re.search(r"\bHKDF\(", path.read_text(encoding="utf-8")):
            found.append(rel)
    assert found == []


# ---- the root ---------------------------------------------------------------


def test_the_root_is_the_secret_as_utf8_bytes():
    assert keyring.root() == SECRET.encode("utf-8")


def test_without_the_secret_there_is_no_root(monkeypatch):
    monkeypatch.delenv("AI_KEY_SECRET")
    with pytest.raises(keyring.Unavailable):
        keyring.root()
    with pytest.raises(keyring.Unavailable):
        keyring.derive(keyring.SHARE_DIGEST)
    monkeypatch.setenv("AI_KEY_SECRET", "")
    with pytest.raises(keyring.Unavailable):
        keyring.root()


@pytest.mark.parametrize("opt_in", [None, "", "false", "0", "no", "off-by-typo"])
def test_the_development_placeholder_is_no_root_without_its_opt_in(monkeypatch, opt_in):
    monkeypatch.setenv("AI_KEY_SECRET", keyring.DEV_SECRET)
    if opt_in is not None:
        monkeypatch.setenv("ROUNDS_ALLOW_DEV_KEY", opt_in)
    with pytest.raises(keyring.Unavailable):
        keyring.root()
    assert keyring.status() == keyring.Status(False, "development-placeholder")


@pytest.mark.parametrize("opt_in", ["true", "TRUE", " yes ", "1"])
def test_the_development_compose_files_opt_in_to_the_placeholder(monkeypatch, opt_in):
    monkeypatch.setenv("AI_KEY_SECRET", keyring.DEV_SECRET)
    monkeypatch.setenv("ROUNDS_ALLOW_DEV_KEY", opt_in)
    assert keyring.root() == keyring.DEV_SECRET.encode("utf-8")
    assert keyring.derive(keyring.CREDENTIAL_WRAP) == _hkdf(keyring.CREDENTIAL_WRAP, keyring.DEV_SECRET)


def test_the_opt_in_never_changes_another_secret(monkeypatch):
    monkeypatch.setenv("ROUNDS_ALLOW_DEV_KEY", "true")
    assert keyring.root() == SECRET.encode("utf-8")


@pytest.mark.parametrize("version", [0, 2, True])
def test_there_is_only_root_version_one(version):
    with pytest.raises(keyring.Unavailable):
        keyring.root(version)


def test_the_root_can_come_from_a_given_environment():
    env = {"AI_KEY_SECRET": "another-test-secret-placeholder-0123456789"}
    assert keyring.root(env=env) == env["AI_KEY_SECRET"].encode("utf-8")
    assert keyring.derive(keyring.SHARE_DIGEST, env=env) == _hkdf(keyring.SHARE_DIGEST, env["AI_KEY_SECRET"])
    with pytest.raises(keyring.Unavailable):
        keyring.root(env={})


# ---- saved provider keys ----------------------------------------------------


def test_a_wrapped_key_opens_with_its_binding():
    wrapped = keyring.wrap(KEY, BINDING)
    assert (wrapped.wrap, wrapped.key_version) == ("aad-v1", 1)
    assert len(base64.b64decode(wrapped.nonce, validate=True)) == 12
    # AES-GCM: the key's bytes and a 16-byte tag.
    assert len(base64.b64decode(wrapped.ciphertext, validate=True)) == len(KEY.encode()) + 16
    assert KEY not in wrapped.ciphertext
    assert keyring.unwrap(wrapped, BINDING) == KEY


def test_every_wrap_has_a_fresh_nonce():
    nonces = {keyring.wrap(KEY, BINDING).nonce for _ in range(200)}
    assert len(nonces) == 200


def test_the_associated_data_is_the_canonical_binding():
    aad = keyring._aad(BINDING, 1)
    assert aad == json.dumps(
        ["rounds-aad/v1", ACCOUNT, "ai_credentials", PROVIDER, 1, "api.example.test", 443],
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    key = keyring.derive(keyring.CREDENTIAL_WRAP)
    wrapped = keyring.wrap(KEY, BINDING)
    opened = AESGCM(key).decrypt(base64.b64decode(wrapped.nonce), base64.b64decode(wrapped.ciphertext), aad)
    assert opened == KEY.encode()


OTHER_BINDINGS = {
    "another account": keyring.Binding("acct00000000002", PROVIDER, "api.example.test", 443),
    "another provider": keyring.Binding(ACCOUNT, "prov00000000002", "api.example.test", 443),
    "another host": keyring.Binding(ACCOUNT, PROVIDER, "api.example.test.other", 443),
    "another port": keyring.Binding(ACCOUNT, PROVIDER, "api.example.test", 8443),
}


@pytest.mark.parametrize("other", OTHER_BINDINGS.values(), ids=OTHER_BINDINGS.keys())
def test_a_saved_key_opens_only_for_its_account_provider_and_address(other):
    wrapped = keyring.wrap(KEY, BINDING)
    with pytest.raises(keyring.CredentialUnusable):
        keyring.unwrap(wrapped, other)
    assert keyring.unwrap(wrapped, BINDING) == KEY


def test_the_binding_check_is_the_associated_datas(monkeypatch):
    # A control for the test above: with one associated data for every
    # binding, the other bindings open, so it is the associated data that
    # refuses them there.
    monkeypatch.setattr(keyring, "_aad", lambda binding, version: b"rounds-aad/test-constant")
    wrapped = keyring.wrap(KEY, BINDING)
    for other in OTHER_BINDINGS.values():
        assert keyring.unwrap(wrapped, other) == KEY


def test_a_key_wrapped_under_one_root_doesnt_open_under_another(monkeypatch):
    wrapped = keyring.wrap(KEY, BINDING)
    monkeypatch.setenv("AI_KEY_SECRET", SECRET + "-rotated")
    with pytest.raises(keyring.CredentialUnusable):
        keyring.unwrap(wrapped, BINDING)


def _legacy(plaintext: str, root: str = SECRET) -> keyring.Wrapped:
    """A key as the runner stored it before the keyring: AES-GCM under
    SHA-256 of the root, with no associated data."""
    nonce = secrets.token_bytes(12)
    sealed = AESGCM(hashlib.sha256(root.encode("utf-8")).digest()).encrypt(nonce, plaintext.encode("utf-8"), None)
    return keyring.Wrapped("legacy-v0", 1, base64.b64encode(sealed).decode(), base64.b64encode(nonce).decode())


def test_a_key_saved_before_the_keyring_still_opens():
    assert keyring.unwrap(_legacy(KEY), BINDING) == KEY


def test_a_key_saved_before_the_keyring_needs_the_same_root(monkeypatch):
    wrapped = _legacy(KEY)
    monkeypatch.setenv("AI_KEY_SECRET", SECRET + "-rotated")
    with pytest.raises(keyring.CredentialUnusable):
        keyring.unwrap(wrapped, BINDING)


def test_the_two_wraps_never_open_as_each_other():
    current = keyring.wrap(KEY, BINDING)
    with pytest.raises(keyring.CredentialUnusable):
        keyring.unwrap(keyring.Wrapped("legacy-v0", 1, current.ciphertext, current.nonce), BINDING)
    legacy = _legacy(KEY)
    with pytest.raises(keyring.CredentialUnusable):
        keyring.unwrap(keyring.Wrapped("aad-v1", 1, legacy.ciphertext, legacy.nonce), BINDING)


def _tampered(text: str) -> str:
    raw = bytearray(base64.b64decode(text))
    raw[0] ^= 1
    return base64.b64encode(bytes(raw)).decode()


@pytest.mark.parametrize(
    "change",
    [
        {"wrap": "aad-v2"},
        {"wrap": ""},
        {"key_version": 2},
        {"key_version": 0},
        {"key_version": True},
        {"ciphertext": ""},
        {"ciphertext": "not base64!"},
        {"nonce": ""},
        {"nonce": base64.b64encode(b"\0" * 11).decode()},
        {"nonce": base64.b64encode(b"\0" * 16).decode()},
        {"ciphertext": "tampered"},
        {"nonce": "tampered"},
    ],
)
def test_a_damaged_wrap_is_unusable(change):
    wrapped = keyring.wrap(KEY, BINDING)
    fields = dict(wrapped.__dict__)
    for name, value in change.items():
        fields[name] = _tampered(fields[name]) if value == "tampered" else value
    with pytest.raises(keyring.CredentialUnusable):
        keyring.unwrap(keyring.Wrapped(**fields), BINDING)


def test_an_empty_key_never_opens():
    nonce = secrets.token_bytes(12)
    key = keyring.derive(keyring.CREDENTIAL_WRAP)
    sealed = AESGCM(key).encrypt(nonce, b"", keyring._aad(BINDING, 1))
    wrapped = keyring.Wrapped("aad-v1", 1, base64.b64encode(sealed).decode(), base64.b64encode(nonce).decode())
    with pytest.raises(keyring.CredentialUnusable):
        keyring.unwrap(wrapped, BINDING)


def test_without_a_root_nothing_wraps_or_opens(monkeypatch):
    wrapped, legacy = keyring.wrap(KEY, BINDING), _legacy(KEY)
    monkeypatch.delenv("AI_KEY_SECRET")
    with pytest.raises(keyring.Unavailable):
        keyring.wrap(KEY, BINDING)
    for each in (wrapped, legacy):
        with pytest.raises(keyring.Unavailable):
            keyring.unwrap(each, BINDING)
    monkeypatch.setenv("AI_KEY_SECRET", keyring.DEV_SECRET)
    with pytest.raises(keyring.Unavailable):
        keyring.wrap(KEY, BINDING)


@pytest.mark.parametrize("plaintext", ["", None, 42, "k" * (keyring.MAX_KEY_BYTES + 1)])
def test_only_a_key_wraps(plaintext):
    with pytest.raises(ValueError):
        keyring.wrap(plaintext, BINDING)


def test_the_longest_key_wraps():
    long_key = "k" * keyring.MAX_KEY_BYTES
    assert keyring.unwrap(keyring.wrap(long_key, BINDING), BINDING) == long_key


@pytest.mark.parametrize(
    "fields",
    [
        ("acct0000000001", PROVIDER, "api.example.test", 443),
        ("ACCT00000000001", PROVIDER, "api.example.test", 443),
        (None, PROVIDER, "api.example.test", 443),
        (ACCOUNT, "prov_0000000001", "api.example.test", 443),
        (ACCOUNT, PROVIDER, "", 443),
        (ACCOUNT, PROVIDER, "API.example.test", 443),
        (ACCOUNT, PROVIDER, "api.example.test/v1", 443),
        (ACCOUNT, PROVIDER, "api example.test", 443),
        (ACCOUNT, PROVIDER, "api.example.test", 0),
        (ACCOUNT, PROVIDER, "api.example.test", 65536),
        (ACCOUNT, PROVIDER, "api.example.test", True),
        (ACCOUNT, PROVIDER, "api.example.test", "443"),
    ],
)
def test_a_binding_takes_only_ids_a_host_and_a_port(fields):
    with pytest.raises(ValueError):
        keyring.Binding(*fields)


# ---- startup ----------------------------------------------------------------


def _lines(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == keyring.__name__]


def test_startup_logs_one_line_for_a_loaded_root(caplog):
    caplog.set_level(logging.INFO, logger=keyring.__name__)
    assert keyring.init() == keyring.Status(True, "loaded")
    (line,) = _lines(caplog)
    assert line.levelno == logging.INFO and "AI_KEY_SECRET" in line.getMessage()
    assert SECRET not in line.getMessage()


def test_startup_says_when_the_root_is_short(caplog, monkeypatch):
    monkeypatch.setenv("AI_KEY_SECRET", "short-test-secret")
    caplog.set_level(logging.INFO, logger=keyring.__name__)
    assert keyring.init() == keyring.Status(True, "loaded", short=True)
    (line,) = _lines(caplog)
    assert line.levelno == logging.WARNING and "openssl rand -hex 32" in line.getMessage()
    assert "short-test-secret" not in line.getMessage()


def test_startup_without_the_secret_logs_one_line_and_goes_on(caplog, monkeypatch):
    monkeypatch.delenv("AI_KEY_SECRET")
    caplog.set_level(logging.INFO, logger=keyring.__name__)
    assert keyring.init() == keyring.Status(False, "unset")
    (line,) = _lines(caplog)
    assert line.levelno == logging.WARNING
    assert "AI_KEY_SECRET is unset" in line.getMessage()


def test_startup_with_the_placeholder_names_the_opt_in(caplog, monkeypatch):
    monkeypatch.setenv("AI_KEY_SECRET", keyring.DEV_SECRET)
    caplog.set_level(logging.INFO, logger=keyring.__name__)
    assert keyring.init() == keyring.Status(False, "development-placeholder")
    (line,) = _lines(caplog)
    assert line.levelno == logging.WARNING
    assert "ROUNDS_ALLOW_DEV_KEY=true" in line.getMessage() and keyring.DEV_SECRET not in line.getMessage()


@pytest.mark.parametrize("value", ["maybe", "on", "2"])
def test_startup_stops_on_an_opt_in_that_isnt_true_or_false(monkeypatch, value):
    monkeypatch.setenv("ROUNDS_ALLOW_DEV_KEY", value)
    with pytest.raises(keyring.Malformed, match="ROUNDS_ALLOW_DEV_KEY"):
        keyring.init()


def test_startup_stops_on_a_secret_that_isnt_text():
    # An undecodable byte in the environment arrives as a lone surrogate.
    env = {"AI_KEY_SECRET": "test-secret-\udcff-placeholder-0123456789"}
    assert keyring.status(env) == keyring.Status(False, "malformed")
    with pytest.raises(keyring.Malformed, match="AI_KEY_SECRET") as err:
        keyring.init(env)
    assert "placeholder" not in str(err.value)
    with pytest.raises(keyring.Unavailable):
        keyring.root(env=env)


def test_the_runner_runs_the_startup_check(monkeypatch):
    from fastapi.testclient import TestClient

    from main import app

    monkeypatch.setenv("ROUNDS_ALLOW_DEV_KEY", "maybe")
    with pytest.raises(keyring.Malformed):
        with TestClient(app):
            pass
    monkeypatch.delenv("AI_KEY_SECRET")
    monkeypatch.delenv("ROUNDS_ALLOW_DEV_KEY")
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}


# ---- the log pseudonym key ----------------------------------------------------


def test_the_pseudonym_key_is_random_per_process_without_a_usable_root(caplog, monkeypatch):
    monkeypatch.setenv("AI_KEY_SECRET", keyring.DEV_SECRET)
    obs.reset_pseudonym_key()
    with caplog.at_level(logging.WARNING):
        key = obs._pseudonym_key()
    assert key != _hkdf(keyring.OBS_PSEUDONYM, keyring.DEV_SECRET)
    assert obs._pseudonym_key() == key
    assert any("only match within this process" in r.getMessage() for r in caplog.records)
    monkeypatch.setenv("ROUNDS_ALLOW_DEV_KEY", "true")
    obs.reset_pseudonym_key()
    assert obs._pseudonym_key() == _hkdf(keyring.OBS_PSEUDONYM, keyring.DEV_SECRET)
