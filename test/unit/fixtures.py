"""Canned GoReSym JSON payloads for tests. GoReSym's own pclntab/moduledata parsing
is Mandiant's problem, not ours -- our wrapper only needs to invoke the vendored
binary and correctly parse whatever JSON it emits, so tests mock the subprocess
boundary with realistic output shaped exactly like GoReSym.proto / the project's own
documented README example, rather than needing a real (or fake) Go binary at all.
"""

SUCCESS_PAYLOAD = {
    "Version": "1.20.4",
    "BuildId": "Zb9QmokKTiOUgHKmaIwz/wd2rtE3W9PN-um1Ocdzh/qTdqcTY_jVajHy_-TtYv/Z_kJu9M77OjfijEiHMcF",
    "Arch": "amd64",
    "OS": "linux",
    "TabMeta": {
        "VA": 5174784, "Version": "1.18", "Endianess": "LittleEndian",
        "CpuQuantum": 1, "CpuQuantumStr": "x86/x64", "PointerSize": 8,
    },
    "ModuleMeta": {
        "VA": 5678816, "Types": 4845568, "ETypes": 5171904,
        "Typelinks": {"Data": 5171904, "Len": 695, "Capacity": 695},
        "ITablinks": {"Data": 5174688, "Len": 11, "Capacity": 11},
        "LegacyTypes": {"Data": 0, "Len": 0, "Capacity": 0},
    },
    "Types": [
        {"VA": 4845568, "Str": "main.implantConfig", "Kind": "struct", "Reconstructed": ""},
    ],
    "Interfaces": [],
    "BuildInfo": {
        "GoVersion": "go1.20.4",
        "Path": "github.com/example-org/private-implant-repo/cmd/agent",
        "Main": {"Path": "github.com/example-org/private-implant-repo", "Version": "(devel)", "Sum": "", "Replace": ""},
        "Deps": [
            {"Path": "golang.org/x/sys", "Version": "v0.6.0", "Sum": "h1:fakehash", "Replace": ""},
        ],
        "Settings": [{"Key": "GOARCH", "Value": "amd64"}],
    },
    "Files": [
        "/home/devuser/go/src/github.com/example-org/private-implant-repo/cmd/agent/main.go",
    ],
    "UserFunctions": [
        {"Start": 4198400, "End": 4198656, "PackageName": "main", "FullName": "main.main"},
    ],
    "StdFunctions": [],
    "Strings": [
        {"Str": "beacon check-in failed", "Start": 5500000},
    ],
}

ERROR_PAYLOAD = {"error": "Failed to parse file: unrecognized file format"}
