from pathlib import Path


def test_signup_hook_is_self_contained():
    hook = Path(__file__).resolve().parents[1] / "pb_hooks" / "main.pb.js"
    source = hook.read_text()

    assert "function envTruthy" not in source
    assert '$os.getenv("ROUNDS_DISABLE_SIGNUPS")' in source
    assert "onRecordBeforeCreateRequest" in source
