"""Runs the vendored GoReSym binary (see goresym_service/vendor/, NOTICE) against a
submitted file and parses its JSON output.

GoReSym only reads the target file to statically recover Go symbol/build metadata
(pclntab/moduledata parsing) -- it never executes it, and neither does this wrapper.
Invoked as a subprocess (not a library, since GoReSym ships only as a Go binary) with
an RLIMIT_AS memory cap and a wall-clock timeout, since a malformed or adversarially
crafted binary is exactly the kind of input this tool is designed to be pointed at.
"""
from __future__ import annotations

import dataclasses
import json
import os
import resource
import subprocess

VENDOR_BINARY = os.path.join(os.path.dirname(__file__), "vendor", "GoReSym")


@dataclasses.dataclass
class GoReSymResult:
    ok: bool
    error: str | None
    data: dict | None  # parsed GoReSym JSON, present iff ok
    timed_out: bool
    stdout: str
    stderr: str


def _limit_resources(max_memory_bytes: int):
    def _apply():
        resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))

    return _apply


def run_goresym(
    sample_path: str,
    timeout: int,
    max_memory_mb: int = 1024,
    recover_types: bool = True,
    include_stdlib_packages: bool = False,
    print_file_paths: bool = True,
    extract_strings: bool = False,
    version_override: str = "",
) -> GoReSymResult:
    cmd = [VENDOR_BINARY]
    if recover_types:
        cmd.append("-t")
    if include_stdlib_packages:
        cmd.append("-d")
    if print_file_paths:
        cmd.append("-p")
    if extract_strings:
        cmd.append("-strings")
    if version_override:
        cmd += ["-v", version_override]
    cmd.append(os.path.abspath(sample_path))

    timed_out = False
    stdout = stderr = ""
    returncode = None
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            preexec_fn=_limit_resources(max_memory_mb * 1024 * 1024),
        )
        stdout, stderr, returncode = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as e:
        timed_out = True
        stdout = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = e.stderr.decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")

    if timed_out:
        return GoReSymResult(ok=False, error="extraction_timeout", data=None,
                              timed_out=True, stdout=stdout, stderr=stderr)

    try:
        parsed = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return GoReSymResult(ok=False, error="unparseable_output", data=None,
                              timed_out=False, stdout=stdout, stderr=stderr)

    if isinstance(parsed, dict) and "error" in parsed and returncode != 0:
        return GoReSymResult(ok=False, error=parsed["error"], data=None,
                              timed_out=False, stdout=stdout, stderr=stderr)

    if returncode != 0:
        return GoReSymResult(ok=False, error="goresym_failed", data=None,
                              timed_out=False, stdout=stdout, stderr=stderr)

    return GoReSymResult(ok=True, error=None, data=parsed, timed_out=False, stdout=stdout, stderr=stderr)
