"""GoReSym: recovers Go symbol/build metadata (compiler version, architecture, source
file paths, module/build info, function and type names) from Go-compiled Windows PE /
Linux ELF / Mach-O executables, including stripped binaries, using a vendored prebuilt
copy of Mandiant's GoReSym (see goresym_service/vendor/, NOTICE, LICENSE -- MIT).

Purely static: GoReSym parses the pclntab/moduledata structures Go embeds in the
binary. Never executes the submitted sample.
"""
from __future__ import annotations

import json
import os

from assemblyline_v4_service.common.base import ServiceBase
from assemblyline_v4_service.common.request import ServiceRequest
from assemblyline_v4_service.common.result import (
    Result,
    ResultKeyValueSection,
    ResultSection,
    ResultTableSection,
    TableRow,
)

from goresym_service.runner import run_goresym

_GHIDRA_IMPORT_SCRIPT = os.path.join(
    os.path.dirname(__file__), "vendor", "ghidra_import", "goresym_rename.py"
)


class GoReSym(ServiceBase):
    def __init__(self, config=None) -> None:
        super().__init__(config)

    def start(self) -> None:
        pass

    def execute(self, request: ServiceRequest) -> None:
        max_rows = request.get_param("max_rows_displayed")

        goresym = run_goresym(
            request.file_path,
            timeout=request.get_param("extraction_timeout_seconds"),
            max_memory_mb=request.get_param("max_extraction_memory_mb"),
            recover_types=request.get_param("recover_types"),
            include_stdlib_packages=request.get_param("include_stdlib_packages"),
            print_file_paths=request.get_param("print_file_paths"),
            extract_strings=request.get_param("extract_strings"),
            version_override=request.get_param("version_override"),
        )

        result = Result()

        if goresym.error == "extraction_timeout":
            failed = ResultSection("Extraction timed out",
                                    body="GoReSym did not finish within the configured timeout.")
            failed.set_heuristic(5, signature="extraction_timeout")
            result.add_section(failed)
            request.result = result
            self._save_log(request, goresym)
            return

        if goresym.error in ("unparseable_output", "goresym_failed"):
            failed = ResultSection("Extraction incomplete",
                                    body="GoReSym did not produce parseable output. "
                                         "See the supplementary log for details.")
            failed.set_heuristic(5, signature=goresym.error)
            result.add_section(failed)
            request.result = result
            self._save_log(request, goresym)
            return

        if not goresym.ok:
            not_go = ResultSection(
                "Not a recognized Go binary",
                body=f"GoReSym could not recover Go symbol metadata from this file: {goresym.error}",
            )
            not_go.set_heuristic(4, signature="not_a_go_binary")
            result.add_section(not_go)
            request.result = result
            self._save_log(request, goresym)
            return

        data = goresym.data

        info = ResultKeyValueSection("Go binary metadata")
        info.set_item("go_version", data.get("Version") or "unknown")
        info.set_item("os", data.get("OS") or "unknown")
        info.set_item("arch", data.get("Arch") or "unknown")
        info.set_item("build_id", data.get("BuildId") or "")
        tab_meta = data.get("TabMeta") or {}
        info.set_item("pclntab_version", tab_meta.get("Version") or "unknown")
        info.set_item("pointer_size", tab_meta.get("PointerSize"))
        info.set_heuristic(1, signature="go_binary_recovered")
        result.add_section(info)

        build_info = data.get("BuildInfo") or {}
        main_module = build_info.get("Main") or {}
        deps = build_info.get("Deps") or []
        if main_module.get("Path") or deps:
            module_section = ResultKeyValueSection("Embedded Go module/build info")
            module_section.set_item("main_module_path", main_module.get("Path") or "unknown")
            module_section.set_item("main_module_version", main_module.get("Version") or "")
            module_section.set_item("dependency_count", len(deps))
            module_section.set_heuristic(3, signature="module_info_recovered")
            result.add_section(module_section)

        files = data.get("Files") or []
        if files:
            file_table = ResultTableSection("Embedded source file paths")
            for path in files[:max_rows]:
                file_table.add_row(TableRow(path=path))
            file_table.set_heuristic(2, signature="file_paths_recovered")
            result.add_section(file_table)
            if len(files) > max_rows:
                result.add_section(ResultSection(
                    "File path list truncated",
                    body=f"{len(files) - max_rows} additional path(s) omitted from display "
                         f"(max_rows_displayed={max_rows}); all are in the supplementary raw JSON.",
                ))

        user_functions = data.get("UserFunctions") or []
        if user_functions:
            func_table = ResultTableSection("User-defined functions")
            for fn in user_functions[:max_rows]:
                func_table.add_row(TableRow(
                    name=fn.get("FullName"), package=fn.get("PackageName"),
                    start=hex(fn.get("Start", 0)), end=hex(fn.get("End", 0)),
                ))
            func_table.set_heuristic(6, signature="user_functions_recovered")
            result.add_section(func_table)

        types = data.get("Types") or []
        if types:
            type_table = ResultTableSection("Recovered types")
            for t in types[:max_rows]:
                type_table.add_row(TableRow(name=t.get("Str"), kind=t.get("Kind"), va=hex(t.get("VA", 0))))
            type_table.set_heuristic(7, signature="types_recovered")
            result.add_section(type_table)

        strings_found = data.get("Strings") or []
        if strings_found:
            string_table = ResultTableSection("Extracted Go strings")
            for s in strings_found[:max_rows]:
                string_table.add_row(TableRow(value=s.get("Str"), start=hex(s.get("Start", 0))))
            string_table.set_heuristic(8, signature="strings_recovered")
            result.add_section(string_table)

        request.add_supplementary(
            _GHIDRA_IMPORT_SCRIPT, "goresym_rename.py",
            "Ghidra script (upstream GoReSym, run from Ghidra's Script Manager) that imports "
            "goresym_output.json to rename functions and label pclntab/moduledata in a disassembly.",
        )

        request.result = result
        self._save_log(request, goresym)

    def _save_log(self, request: ServiceRequest, goresym) -> None:
        log_path = os.path.join(self.working_directory, "goresym_output.json")
        with open(log_path, "w") as f:
            if goresym.data is not None:
                json.dump(goresym.data, f, indent=2)
            else:
                f.write(goresym.stdout)
                f.write("\n---- stderr ----\n")
                f.write(goresym.stderr)
        request.add_supplementary(log_path, "goresym_output.json", "Full raw GoReSym output")
