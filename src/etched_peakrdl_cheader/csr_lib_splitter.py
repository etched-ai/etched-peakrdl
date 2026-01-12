from __future__ import annotations

import re
from pathlib import Path

# Functions that wrap/dispatch to other test functions. These are excluded when
# creating split libraries since they would pull in many other functions.
_WRAPPER_FUNCTIONS = {
    "RwTest",
    "TsRwTest",
    "IscTimestampRwTest",
    "ControlRwTest",
}


def split_default_wafersort_libs(out_dir: str) -> None:
    """Split known-bloated wafersort CSR test libraries by bitfield count."""
    out_path = Path(out_dir)
    _split_single_library_by_bitfields(out_path, "dl_bp_csr_rw_test_lib", 8)
    _split_single_library_by_bitfields(out_path, "dl_ctl_top_rw_test_lib", 4)
    _split_isc_csr(out_path)


def split_libraries_by_bitfields(out_dir: str, split_rules: dict[str, int]) -> None:
    """Split generated CSR test libs into *_partN libs balancing bitfield tests.

    This is a post-processing step on generated .cc/.h files. It partitions
    leaf register-test functions across N parts using a greedy algorithm based
    on the number of BitFieldWriteReadTest* calls per function.
    """
    out_path = Path(out_dir)
    for lib_name, num_parts in split_rules.items():
        if num_parts <= 1:
            continue
        _split_single_library_by_bitfields(out_path, lib_name, num_parts)


def _split_isc_csr(out_dir: Path) -> None:
    """Keep isc_csr split stable for existing wafersort test apps."""
    lib_name = "isc_csr_rw_test_lib"
    cc_path = out_dir / f"{lib_name}.cc"
    h_path = out_dir / f"{lib_name}.h"
    if not cc_path.exists() or not h_path.exists():
        return

    functions = _parse_cc_for_function_bodies(cc_path)
    functions = {
        name: body for name, body in functions.items() if name not in _WRAPPER_FUNCTIONS
    }
    if not functions:
        return

    header_text, namespace_name = _extract_header_and_namespace(cc_path)
    decls = _parse_header_declarations(h_path)

    part1 = [
        "Desc0RwTest",
        "Desc1RwTest",
        "IntcRwTest",
        "SaColRwTest",
        "MemoryControlRwTest",
        "AxiSettingRwTest",
    ] + [f"Start{i}IscTimestampRwTest" for i in range(26)]

    part2 = [f"Start{i}IscTimestampRwTest" for i in range(26, 32)] + [
        f"Done{i}IscTimestampRwTest" for i in range(31)
    ]

    part3 = [
        "Done31IscTimestampRwTest",
        "GlobalEnableIscTimestampRwTest",
        "LocalControlIscTimestampRwTest",
    ]

    _split_single_library_fixed_parts(
        out_dir,
        lib_name,
        namespace_name,
        header_text,
        functions,
        decls,
        [part1, part2, part3],
    )


def _split_single_library_by_bitfields(out_dir: Path, lib_name: str, num_parts: int) -> None:
    cc_path = out_dir / f"{lib_name}.cc"
    h_path = out_dir / f"{lib_name}.h"
    if not cc_path.exists() or not h_path.exists():
        return

    functions = _parse_cc_for_function_bodies(cc_path)
    functions = {
        name: body for name, body in functions.items() if name not in _WRAPPER_FUNCTIONS
    }
    if not functions:
        return

    header_text, namespace_name = _extract_header_and_namespace(cc_path)
    decls = _parse_header_declarations(h_path)

    func_bitfields = {name: _count_bitfields(body) for name, body in functions.items()}

    # Stable sort: ties preserve original file order since dicts preserve
    # insertion order and Python's sort is stable.
    sorted_funcs = sorted(func_bitfields.keys(), key=lambda x: -func_bitfields[x])

    parts: list[list[str]] = [[] for _ in range(num_parts)]
    part_totals = [0] * num_parts

    for func_name in sorted_funcs:
        min_idx = part_totals.index(min(part_totals))
        parts[min_idx].append(func_name)
        part_totals[min_idx] += func_bitfields[func_name]

    for part_idx, part_funcs in enumerate(parts):
        if not part_funcs:
            continue
        split_name = f"{lib_name}_part{part_idx + 1}"
        _write_part_header(out_dir, split_name, namespace_name, part_idx + 1, part_funcs, decls)
        _write_part_cc(
            out_dir,
            split_name,
            lib_name,
            namespace_name,
            part_idx + 1,
            header_text,
            functions,
            part_funcs,
        )


def _split_single_library_fixed_parts(
    out_dir: Path,
    lib_name: str,
    namespace_name: str,
    header_text: str,
    functions: dict[str, str],
    decls: dict[str, str],
    parts: list[list[str]],
) -> None:
    for part_idx, part_funcs in enumerate(parts):
        filtered_funcs = [name for name in part_funcs if name in functions]
        if not filtered_funcs:
            continue
        split_name = f"{lib_name}_part{part_idx + 1}"
        _write_part_header(
            out_dir,
            split_name,
            namespace_name,
            part_idx + 1,
            filtered_funcs,
            decls,
        )
        _write_part_cc(
            out_dir,
            split_name,
            lib_name,
            namespace_name,
            part_idx + 1,
            header_text,
            functions,
            filtered_funcs,
        )


def _count_bitfields(func_body: str) -> int:
    return func_body.count("BitFieldWriteReadTest")


def _parse_header_declarations(header_path: Path) -> dict[str, str]:
    content = header_path.read_text()

    decl_pattern = re.compile(
        r"(sival::wafersort::TestResult\s+(\w+)\s*\([^;]+\);)",
        re.MULTILINE | re.DOTALL,
    )

    decls: dict[str, str] = {}
    for match in decl_pattern.finditer(content):
        full_decl = match.group(1).strip()
        func_name = match.group(2)
        decls[func_name] = full_decl

    return decls


def _parse_cc_for_function_bodies(cc_path: Path) -> dict[str, str]:
    content = cc_path.read_text()
    functions: dict[str, str] = {}

    lines = content.split("\n")
    current_func: str | None = None
    func_lines: list[str] = []
    brace_count = 0
    in_function = False

    func_start_pattern = re.compile(r"^sival::wafersort::TestResult\s+(\w+)\s*\(")

    for line in lines:
        match = func_start_pattern.match(line)
        if match and not in_function:
            current_func = match.group(1)
            func_lines = [line]
            brace_count = line.count("{") - line.count("}")
            in_function = brace_count > 0 or "{" not in line
            continue

        if in_function:
            func_lines.append(line)
            brace_count += line.count("{") - line.count("}")

            if brace_count == 0 and "{" in "".join(func_lines):
                if current_func is not None:
                    functions[current_func] = "\n".join(func_lines)
                current_func = None
                func_lines = []
                in_function = False

    return functions


def _extract_header_and_namespace(cc_path: Path) -> tuple[str, str]:
    content = cc_path.read_text()
    lines = content.split("\n")

    header_lines: list[str] = []
    namespace_name: str | None = None
    in_multiline_macro = False

    for line in lines:
        if in_multiline_macro:
            header_lines.append(line)
            if not line.rstrip().endswith("\\"):
                in_multiline_macro = False
            continue

        if (
            line.startswith("#include")
            or line.startswith("#ifndef")
            or line.startswith("#ifdef")
            or line.startswith("#define")
            or line.startswith("#else")
            or line.startswith("#endif")
            or line.strip() == ""
            or line.startswith("//")
        ):
            header_lines.append(line)
            if line.rstrip().endswith("\\"):
                in_multiline_macro = True
            continue

        match = re.match(r"^namespace\s+(\w+)\s*\{", line)
        if match:
            namespace_name = match.group(1)
            break

    if namespace_name is None:
        raise ValueError(f"Failed to find namespace in {cc_path}")

    header_text = "\n".join(header_lines)
    return header_text, namespace_name


def _write_part_header(
    out_dir: Path,
    split_name: str,
    namespace_name: str,
    part_num: int,
    part_funcs: list[str],
    decls: dict[str, str],
) -> None:
    out_path = out_dir / f"{split_name}.h"
    part_namespace = f"{namespace_name}Part{part_num}"

    decl_lines: list[str] = []
    for func_name in part_funcs:
        decl = decls.get(func_name)
        if decl is None:
            raise ValueError(
                f"Missing declaration for {func_name} in {split_name}.h"
            )
        decl_lines.append(decl)

    content = (
        "#pragma once\n\n"
        "#include <cstdint>\n\n"
        '#include "fw/soc/sohu/sohu_chip_csr.h"\n'
        '#include "sival/wafersort/sival_helper.h"\n\n'
        f"namespace {part_namespace} {{\n"
        + "\n".join(decl_lines)
        + f"\n}}  // namespace {part_namespace}\n"
    )

    out_path.write_text(content)


def _write_part_cc(
    out_dir: Path,
    split_name: str,
    lib_name: str,
    namespace_name: str,
    part_num: int,
    header_text: str,
    functions: dict[str, str],
    part_funcs: list[str],
) -> None:
    out_path = out_dir / f"{split_name}.cc"
    part_namespace = f"{namespace_name}Part{part_num}"

    new_header = header_text.replace(
        f'#include "{lib_name}.h"', f'#include "{split_name}.h"'
    )

    body = "\n\n".join(functions[func_name] for func_name in part_funcs)
    content = (
        f"{new_header}\n"
        f"namespace {part_namespace} {{\n\n"
        f"{body}\n\n"
        f"}}  // namespace {part_namespace}\n"
    )

    out_path.write_text(content)
