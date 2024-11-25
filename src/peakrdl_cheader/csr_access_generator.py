from typing import TextIO, Set, Optional, List
import os

from systemrdl.walker import RDLListener, RDLWalker, WalkerAction
from systemrdl.node import (
    AddrmapNode,
    AddressableNode,
    RegNode,
    RegfileNode,
    SignalNode,
    FieldNode,
    Node,
    MemNode,
)

from .design_state import DesignState
from .identifier_filter import kw_filter as kwf
from . import utils


class CsrAccessGenerator(RDLListener):
    def __init__(self, ds: DesignState) -> None:
        self.ds = ds
        self.indent_level = 0
        self.rootdir: str
        self.fbuild: TextIO
        self.f_test_idx_map: TextIO
        self.traversed = set()
        self.test_idx = 0
        self.array_nest_lvl = 0

        self.root_node: AddrmapNode
        self.root_node = None
        self.stack = []

        self.f: TextIO
        self.f = None  # type: ignore

    def run(self, rootdir: str, top_node: AddrmapNode) -> None:
        self.rootdir = rootdir
        self.fbuild = open(rootdir + "BUILD", "w")
        self.fbuild.write('load("@rules_cc//cc:defs.bzl", "cc_library")\n\n')
        self.f_test_idx_map = open(
            rootdir + f".{top_node.inst_name}_text_idx_map.txt", "w"
        )
        self.root_node = top_node
        RDLWalker().walk(top_node, self)
        self.fbuild.close()
        self.f_test_idx_map.close()

    def get_node_prefix(self, node: AddressableNode) -> str:
        return utils.get_node_prefix(self.ds, self.root_node, node)

    def get_struct_name(self, node: AddressableNode) -> str:
        return utils.get_struct_name(self.ds, self.root_node, node)

    def get_friendly_name(self, node: Node) -> str:
        return utils.get_friendly_name(self.ds, self.root_node, node)

    def get_addrmap_relative_name(self, node: Node) -> str:
        stk = []
        curr = node
        while type(curr) is not AddrmapNode:
            stk.append(curr.inst_name)
            curr = curr.parent
        return ("_".join(stk)).title().replace("_", "")

    def get_prefix(self, node: Node) -> str:
        # Returns node prefix while maintaining lack of collisions if
        # file is custom rebuilt based on directives and therefore
        # differs from base version
        # Note: Changed from using rebuild as flag for rebuild to !unique,
        # ensuring no repeats unless in array
        if node.rebuild:
            root = node
            while root.rebuild:
                root = root.parent
            return (
                self.get_node_prefix(root)
                + "_"
                + node.get_rel_path(
                    root, hier_separator="_", array_suffix="", empty_array_suffix=""
                )
            )
        else:
            return utils.get_node_prefix(self.ds, node, node)

    def get_file_prefix(self, node: Node) -> str:
        # Returns name of node for .cc and .h files
        return self.get_prefix(node) + "_rw_test_lib"

    def get_namespace_name(self, node: Node) -> str:
        # Returns namespace name of node
        return self.get_prefix(node).title().replace("_", "") + "RwTestLib"

    def get_reg_test_name(self, node: Node) -> str:
        # Returns test name for function that tests one register
        return self.get_addrmap_relative_name(node) + "RwTest"

    def get_test_function_name(self, node: RegNode) -> str:
        # Returns test name for a specific field, which varies based on
        # the width of the register
        if node.size == 32:  # 32 bytes = 256 bits
            return "BitFieldWriteReadTest256"
        elif node.size == 4:  # 4 bytes = 32 bits
            return "BitFieldWriteReadTest32"
        else:
            raise ValueError(
                f"Unexpected regwidth of {node.size} for node {node.inst_name} | {self.get_struct_name(node)}"
            )

    def enter_Addrmap(self, node: AddrmapNode) -> Optional[WalkerAction]:
        if (self.get_prefix(node) in self.traversed) or node.ignore:
            return WalkerAction.SkipDescendants
        if node.is_array:
            self.array_nest_lvl += 1
        self.test_idx = 1
        path = self.rootdir + self.get_file_prefix(node) + ".cc"
        self.generateHeader(node)  # Creates .h file for addrmapnode
        fp = open(path, "w")

        # Test if has AddrmapNodes
        addrmapnodes = dict()
        hasRegOrRegFile = False
        for child in node.children():
            if child.ignore:
                continue
            if type(child) is AddrmapNode:
                addrmapnodes[self.get_prefix(child)] = child
            if (type(child) is RegNode) or (type(child) is RegfileNode):
                hasRegOrRegFile = True

        self.stack.append((fp, hasRegOrRegFile))

        self.writeBUILD(node)

        fp.write(f'#include "{self.get_file_prefix(node)}.h"\n')  # Include self
        deplist = [
            f'#include "{self.get_file_prefix(child)}.h"'
            for child in addrmapnodes.values()
        ]
        context = {"hasRegOrRegFile": hasRegOrRegFile, "deps": deplist}
        template = self.ds.jj_env.get_template("rw_test_registers_header.c")
        template.stream(context).dump(fp)
        fp.write("\n")
        fp.write(f"namespace {self.get_namespace_name(node)} {{\n")
        return WalkerAction.Continue

    def exit_Addrmap(self, node: AddrmapNode) -> Optional[WalkerAction]:
        if (self.get_prefix(node) in self.traversed) or node.ignore:
            return WalkerAction.Continue
        if node.is_array:
            self.array_nest_lvl -= 1
        self.traversed.add(self.get_prefix(node))

        (fp, _) = self.stack.pop()
        addr_ptr = self.get_node_prefix(node) + "_addr"
        fp.write(
            f"bool RwTest(volatile {self.get_struct_name(node)} &{addr_ptr}, uint64_t test_idx) {{\n"
        )
        fp.write("  bool passed = true;\n")

        for child in node.children():
            if child.ignore:
                continue
            if type(child) is SignalNode:
                continue
            if type(child) is AddrmapNode:
                structmember = kwf(child.inst_name)
                if child.is_array:
                    for i in range(child.array_dimensions[0]):
                        if i in child.ignore_idxes:
                            continue
                        fp.write("  if (passed) {\n")
                        fp.write(
                            # f"    passed = {self.get_namespace_name(child)}::RwTest({addr_ptr}.{structmember}[{i}], test_idx | (uint64_t){hex(i)} << {(5 - (self.array_nest_lvl)) * 8});\n"
                            f"    passed = {self.get_namespace_name(child)}::RwTest({addr_ptr}.{structmember}[{i}], test_idx);\n"
                        )
                        fp.write("  }\n")
                else:
                    fp.write("  if (passed) {\n")
                    fp.write(
                        f"    {self.get_namespace_name(child)}::RwTest({addr_ptr}.{structmember}, test_idx);\n"
                    )
                    fp.write("  }\n")
            if (type(child) is RegNode) or (type(child) is RegfileNode):
                addrptr = ""
                if type(child) is RegNode:
                    addrptr = f"reinterpret_cast<volatile __uint128_t*>(&{addr_ptr}.{child.inst_name}"
                else:
                    addrptr = f"({addr_ptr}.{child.inst_name}"
                if child.is_array:
                    for i in range(child.array_dimensions[0]):
                        if i in child.ignore_idxes:
                            continue

                        fp.write("  if (passed) {\n")
                        fp.write(
                            # f"    passed &= {self.get_reg_test_name(child)}({addrptr}[{i}]), test_idx | (uint64_t){hex(i)} << {(5 - (self.array_nest_lvl)) * 8});\n"
                            f"    passed &= {self.get_reg_test_name(child)}({addrptr}[{i}]), test_idx);\n"
                        )
                        fp.write("  }\n")
                else:
                    fp.write("  if (passed) {\n")
                    fp.write(
                        f"    passed &= {self.get_reg_test_name(child)}({addrptr}), test_idx);\n"
                    )
                    fp.write("  }\n")
        fp.write("  return passed;\n")
        fp.write("}\n")  # bool RwTest

        fp.write(f"}} // end {self.get_namespace_name(node)} namespace\n")
        fp.close()
        return WalkerAction.Continue

    def enter_Regfile(self, node: RegfileNode) -> Optional[WalkerAction]:
        if node.ignore:
            return WalkerAction.SkipDescendants

        if node.is_array:
            self.array_nest_lvl += 1
        return WalkerAction.Continue

    def exit_Regfile(self, node: RegfileNode) -> Optional[WalkerAction]:
        if node.ignore:
            return WalkerAction.Continue

        (curr_fp, _) = self.stack[-1]
        addr_ptr = self.get_node_prefix(node) + "_addr"
        if node.is_array:
            self.array_nest_lvl -= 1
        curr_fp.write(
            f"bool {self.get_reg_test_name(node)}(volatile {self.get_struct_name(node)} &{addr_ptr}, uint64_t test_idx) {{\n"
        )
        curr_fp.write("  bool passed = true;\n")
        for child in node.children():
            if child.ignore:
                continue
            if type(child) is SignalNode:
                continue
            addrptr = ""
            if type(child) is RegNode:
                addrptr = f"reinterpret_cast<volatile __uint128_t*>(&{addr_ptr}.{child.inst_name}"
            else:
                addrptr = f"({addr_ptr}.{child.inst_name}"
            if child.is_array:
                for i in range(child.array_dimensions[0]):
                    if i in child.ignore_idxes:
                        continue

                    curr_fp.write("  if (passed) {\n")
                    curr_fp.write(
                        # f"    passed &= {self.get_reg_test_name(child)}({addrptr}[{i}]), test_idx | (uint64_t){hex(i)} << {(5 - (self.array_nest_lvl)) * 8});\n"
                        f"    passed &= {self.get_reg_test_name(child)}({addrptr}[{i}]), test_idx);\n"
                    )
                    curr_fp.write("  }\n")
            else:
                curr_fp.write("  if (passed) {\n")
                curr_fp.write(
                    f"    passed &= {self.get_reg_test_name(child)}({addrptr}), test_idx);\n"
                )
                curr_fp.write("  }\n")
        curr_fp.write("  return passed;\n")
        curr_fp.write("}\n")
        return WalkerAction.Continue

    def enter_Reg(self, node: RegNode) -> Optional[WalkerAction]:
        if node.ignore:
            return WalkerAction.SkipDescendants
        prefix = self.get_node_prefix(node).upper()
        addr = node.inst_name + "_addr"
        (curr_fp, _) = self.stack[-1]

        curr_fp.write(f"// {self.get_friendly_name(node)}\n")
        curr_fp.write(
            f"bool {self.get_reg_test_name(node)}(volatile __uint128_t* {addr}, uint64_t test_idx) {{\n"
        )
        curr_fp.write("  bool passed = true;\n\n")

        mask_checks = []
        needs_check = False
        needs_readonly = False
        needs_writeonly = False
        needs_singlepulse = False
        for field in node.fields():
            if field.ignore or (not field.is_sw_readable and not field.is_sw_writable):
                continue
            if field.is_sw_readable and not field.is_sw_writable:
                needs_readonly = True
            elif field.is_sw_writable and not field.is_sw_readable:
                needs_writeonly = True
            elif field.is_sw_writable and field.is_sw_readable:
                if field.get_property("singlepulse"):
                    needs_singlepulse = True
                else:
                    needs_check = True

        if needs_check:
            curr_fp.write("  uint64_t curr_test_idx;\n")
            curr_fp.write(
                "  fw::app::csr_access_test::CsrTestIgnorer* ignorer = fw::app::csr_access_test::CsrTestIgnorer::GetCsrTestIgnorer();\n"
            )
        if needs_readonly:
            curr_fp.write("  fw::utils::Csr256BitValue read_only_mask{0,0};\n")
            mask_checks.append(
                f"fw::testing::ReadCsrMasked256({addr}, read_only_mask);\n"
            )
        if needs_writeonly:
            curr_fp.write("  fw::utils::Csr256BitValue write_only_mask{0,0};\n")
            mask_checks.append(
                f"fw::testing::WriteCsrMasked256({addr}, write_only_mask);\n"
            )
        if needs_singlepulse:
            curr_fp.write("  fw::utils::Csr256BitValue singlepulse_mask{0,0};\n")
            mask_checks.append(
                f"fw::testing::WriteReadCsrMasked256({addr}, singlepulse_mask);\n"
            )

        casted_addr = addr
        # Checks for register width and applies proper size cast
        if node.size != 32:
            if node.size == 4:
                pointer_type = "uint32_t"
            else:
                raise ValueError(
                    f"Unexpected value of {node.size} in {node.inst_name}\n"
                )
            casted_addr = f"reinterpret_cast<volatile {pointer_type}*>({addr})"

        for field in node.fields():
            field_prefix = prefix + "__" + field.inst_name.upper()

            if field.ignore:
                curr_fp.write(
                    f"  // {field_prefix} has been ignored via injected directives\n\n"
                )
                continue

            if not field.is_sw_writable and not field.is_sw_readable:
                print(f"Field is not sw writeable or sw readable: {field_prefix}")
                continue

            if not field.is_sw_writable:
                curr_fp.write(f"  // {field_prefix} is software read-only\n")
                curr_fp.write(
                    f"  fw::testing::AddBitsToMask256(&read_only_mask, {field_prefix}_bp, {field_prefix}_bw);\n\n"
                )
                continue

            if not field.is_sw_readable:
                curr_fp.write(f"  // {field_prefix} is software write-only\n")
                curr_fp.write(
                    f"  fw::testing::AddBitsToMask256(&write_only_mask, {field_prefix}_bp, {field_prefix}_bw);\n\n"
                )
                continue

            if field.get_property("singlepulse"):
                curr_fp.write(f"  // {field_prefix} is singlepulse\n")
                curr_fp.write(
                    f"  fw::testing::AddBitsToMask256(&singlepulse_mask, {field_prefix}_bp, {field_prefix}_bw);\n\ngit"
                )
                continue

            context = {
                "reg_ptr": f"{casted_addr}",
                "function_name": f"{self.get_test_function_name(node)}",
                "field": f"{prefix}::{field.inst_name.upper()}",
                "field_bp": f"{field_prefix}_bp",
                "field_bw": f"{field_prefix}_bw",
                "test_idx": f"{hex(self.test_idx)}",
            }
            self.writeTestIdxMap(hex(self.test_idx), field)

            self.test_idx += 1
            template = self.ds.jj_env.get_template("rw_readwrite_test.c")
            template.stream(context).dump(curr_fp)
            curr_fp.write("\n\n")
        for mask_check in mask_checks:
            curr_fp.write(mask_check)
        curr_fp.write("  return passed;\n")
        curr_fp.write("}\n\n")  # RwTest
        return WalkerAction.SkipDescendants

    def generateHeader(self, node: AddrmapNode) -> None:
        header_path = self.rootdir + self.get_file_prefix(node) + ".h"
        header_fp = open(header_path, "w")

        context = {
            "namespace": self.get_namespace_name(node),
            "struct_type_name": self.get_struct_name(node),
        }
        template = self.ds.jj_env.get_template("rw_test_lib_header.h")
        template.stream(context).dump(header_fp)
        childstk = list(node.children())
        while childstk:
            child = childstk.pop(0)
            if child.ignore:
                continue
            if type(child) is RegfileNode:
                childstk = list(child.children()) + childstk
                header_fp.write(
                    f"  bool {self.get_reg_test_name(child)}(volatile {self.get_struct_name(child)}&, uint64_t);\n"
                )
                continue
            if type(child) is RegNode:
                header_fp.write(
                    f"  bool {self.get_reg_test_name(child)}(volatile __uint128_t*, uint64_t);\n"
                )
        header_fp.write("}\n")
        header_fp.close()

    def writeBUILD(self, node: AddrmapNode) -> None:
        filename = self.get_file_prefix(node)
        impl_deps = set()
        for child in node.children():
            if child.ignore:
                continue
            if isinstance(child, AddrmapNode):
                impl_deps.add(f":{self.get_file_prefix(child)}")
        context = {
            "name": filename,
            "srcs": filename + ".cc",
            "hdrs": filename + ".h",
            "impl_deps": list(impl_deps),
        }
        template = self.ds.jj_env.get_template("BUILD_TEMPLATE")
        template.stream(context).dump(self.fbuild)

    def writeTestIdxMap(self, idx: int, node: AddrmapNode) -> None:
        self.f_test_idx_map.write(f"{idx} {node.get_path()}\n")
