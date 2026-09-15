# GoReSym

Docker Hub: [kylemc54321/assemblyline-service-goresym](https://hub.docker.com/r/kylemc54321/assemblyline-service-goresym)

An AssemblyLine v4 service that recovers Go symbol and build metadata — compiler
version, architecture, embedded source file paths, module/dependency info, and
function/type names — from Go-compiled Windows PE / Linux ELF / Mach-O executables,
**including stripped binaries**, using a vendored prebuilt copy of
[Mandiant's GoReSym](https://github.com/mandiant/GoReSym).

This is purely static analysis: GoReSym parses the `pclntab`/`moduledata` structures
the Go compiler embeds in every binary it produces (this metadata survives symbol
stripping, unlike a typical ELF/PE symbol table). **This service never executes the
submitted sample.**

## Why this is useful for triage

Go malware is very commonly built with `-ldflags="-s -w"` (strip debug info/symbol
table) to hinder analysis, but GoReSym recovers function and type names anyway by
walking Go's own runtime metadata structures instead of the stripped symbol table. Two
signals it recovers are particularly useful for attribution:

- **Embedded source file paths** (heuristic 2): the build machine's own directory
  layout, e.g. `/home/devuser/go/src/github.com/...` or `C:\Users\...`.
- **Embedded Go module path** (heuristic 3, via `debug.ReadBuildInfo`): often reveals
  the malware author's private repository name/path.

## License

This repository is MIT licensed. It vendors an **unmodified, prebuilt** GoReSym Linux
binary (`goresym_service/vendor/GoReSym`), also MIT licensed by Mandiant — see `NOTICE`
and `goresym_service/vendor/GoReSym_LICENSE` (copied verbatim) for provenance.

## How it works

The vendored binary is invoked as a subprocess (it ships only as a compiled Go binary,
not a library), with `RLIMIT_AS` and a wall-clock timeout applied, since a malformed or
adversarially crafted binary is exactly the kind of input GoReSym is meant to be
pointed at. Its JSON output is parsed directly — the schema is documented in
[GoReSym.proto](https://github.com/mandiant/GoReSym/blob/master/GoReSym.proto) from the
upstream project. The full raw JSON is always attached as a supplementary file; the
result sections shown in the UI are capped (`max_rows_displayed`) since a large binary
can embed thousands of functions/types.

## Submission parameters

| Param | Default | Purpose |
|---|---|---|
| `extraction_timeout_seconds` | 60 | Wall-clock timeout for the GoReSym subprocess. |
| `max_extraction_memory_mb` | 1024 | `RLIMIT_AS` cap on the GoReSym subprocess. |
| `max_rows_displayed` | 200 | Cap on rows shown per table (files/functions/types/strings); full data is always in the supplementary JSON. |
| `recover_types` | true | Passes `-t` (recover Go type/interface structures). |
| `include_stdlib_packages` | false | Passes `-d` (also list standard-library functions, usually very noisy). |
| `print_file_paths` | true | Passes `-p` (recover embedded source file paths). |
| `extract_strings` | false | Passes `-strings` (extract the Go string-intern table; can be large/slow). |
| `version_override` | "" | Passes `-v <version>` to override automated Go version detection, for cases where it fails. |

## Development

This system's Python is externally managed (PEP 668); use an isolated virtualenv:

```bash
python3 -m venv .venv
.venv/bin/pip install assemblyline-v4-service assemblyline-service-utilities pytest pyyaml
.venv/bin/pytest test/
```

No test in this repo invokes the real vendored GoReSym binary against an actual Go
binary. GoReSym's own binary-format parsing is Mandiant's problem, not this wrapper's
— tests mock the `subprocess.run` boundary with a canned, schema-accurate JSON payload
(see `test/unit/fixtures.py`, shaped after GoReSym's own documented README example)
and verify this service's own flag-construction/parsing/result-building logic against
it. The sample fixture in `test/samples/*.cart` is therefore just an arbitrary
placeholder file, not a real or real-shaped executable.
