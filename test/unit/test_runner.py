import json
import subprocess
from unittest.mock import patch

from goresym_service.runner import run_goresym
from test.unit.fixtures import ERROR_PAYLOAD, SUCCESS_PAYLOAD


def _completed(stdout, returncode=0, stderr=""):
    return subprocess.CompletedProcess(args=["GoReSym"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_success_parses_json():
    with patch("goresym_service.runner.subprocess.run", return_value=_completed(json.dumps(SUCCESS_PAYLOAD))):
        result = run_goresym("/tmp/whatever", timeout=30)

    assert result.ok
    assert result.error is None
    assert result.data["Version"] == "1.20.4"
    assert result.data["Arch"] == "amd64"


def test_error_payload_reported_not_ok():
    with patch("goresym_service.runner.subprocess.run",
               return_value=_completed(json.dumps(ERROR_PAYLOAD), returncode=1)):
        result = run_goresym("/tmp/whatever", timeout=30)

    assert not result.ok
    assert result.error == ERROR_PAYLOAD["error"]
    assert result.data is None


def test_timeout_reported():
    with patch("goresym_service.runner.subprocess.run",
               side_effect=subprocess.TimeoutExpired(cmd=["GoReSym"], timeout=30)):
        result = run_goresym("/tmp/whatever", timeout=30)

    assert not result.ok
    assert result.timed_out
    assert result.error == "extraction_timeout"


def test_unparseable_output_reported_not_crashed():
    with patch("goresym_service.runner.subprocess.run",
               return_value=_completed("not json at all", returncode=0)):
        result = run_goresym("/tmp/whatever", timeout=30)

    assert not result.ok
    assert result.error == "unparseable_output"


def test_flags_are_passed_through():
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _completed(json.dumps(SUCCESS_PAYLOAD))

    with patch("goresym_service.runner.subprocess.run", side_effect=fake_run):
        run_goresym(
            "/tmp/whatever", timeout=30, recover_types=True, include_stdlib_packages=True,
            print_file_paths=False, extract_strings=True, version_override="1.19",
        )

    cmd = captured["cmd"]
    assert "-t" in cmd
    assert "-d" in cmd
    assert "-p" not in cmd
    assert "-strings" in cmd
    assert "-v" in cmd and "1.19" in cmd
