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


class PerfCounterGenerator(RDLListener):
    def __init__(self, ds: DesignState) -> None:
        self.ds = ds
        self.indent_level = 0
        self.rootdir: str
        self.curr_fp: TextIO
        self.traversed = set()
        self.test_idx = 0
        self.array_nest_lvl = 0
        self.idx_ascii = ord("i")
        self.stringstack = []
        self.structstack = []

        self.root_node: AddrmapNode
        self.root_node = None
        self.stack = []

        self.f: TextIO
        self.f = None  # type: ignore

    def run(self, rootdir: str, top_node: AddrmapNode) -> None:
        self.rootdir = rootdir
        self.root_node = top_node
        self.curr_fp = open(rootdir + "test.cc", "w")
        RDLWalker().walk(top_node, self)
        self.curr_fp.close()

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
            return "bit_field_write_read_32bit_test"
        else:
            raise ValueError(
                f"Unexpected regwidth of {node.size} for node {node.inst_name} | {self.get_struct_name(node)}"
            )

    def enter_Addrmap(self, node: AddrmapNode) -> Optional[WalkerAction]:
        if (self.get_prefix(node) in self.traversed) or node.ignore:
            return WalkerAction.SkipDescendants

        structmember = kwf(node.inst_name)
        stringmember = kwf(node.inst_name)
        if node.is_array:
            self.curr_fp.write(
                f"for(size_t {chr(self.idx_ascii)} = 0; i < {node.array_dimensions[0]}; i++) {{\n"
            )
            structmember += f"[{chr(self.idx_ascii)}]"
            stringmember += "[]"
            self.idx_ascii += 1
        self.structstack.append(structmember)
        self.stringstack.append(stringmember)

        return WalkerAction.Continue

    def exit_Addrmap(self, node: AddrmapNode) -> Optional[WalkerAction]:
        if (self.get_prefix(node) in self.traversed) or node.ignore:
            return WalkerAction.Continue

        self.structstack.pop(-1)
        self.stringstack.pop(-1)
        if node.is_array:
            self.idx_ascii += 1
            self.curr_fp.write("}\n")

        return WalkerAction.Continue

    def enter_Regfile(self, node: RegfileNode) -> Optional[WalkerAction]:
        if node.ignore:
            return WalkerAction.SkipDescendants

        structmember = kwf(node.inst_name)
        stringmember = kwf(node.inst_name)
        if node.is_array:
            self.curr_fp.write(
                f"for(size_t {chr(self.idx_ascii)} = 0; i < {node.array_dimensions[0]}; i++) {{\n"
            )
            structmember += f"[{chr(self.idx_ascii)}]"
            stringmember += "[]"
            self.idx_ascii += 1
        self.structstack.append(structmember)
        self.stringstack.append(stringmember)

        return WalkerAction.Continue

    def exit_Regfile(self, node: RegfileNode) -> Optional[WalkerAction]:
        if node.ignore:
            return WalkerAction.Continue

        self.structstack.pop(-1)
        self.stringstack.pop(-1)
        if node.is_array:
            self.idx_ascii += 1
            self.curr_fp.write("}\n")

        return WalkerAction.Continue

    def enter_Reg(self, node: RegNode) -> Optional[WalkerAction]:
        if node.ignore:
            return WalkerAction.SkipDescendants
        structmember = kwf(node.inst_name)
        stringmember = kwf(node.inst_name)
        if node.is_array:
            structmember += f"[{chr(self.idx_ascii)}]"
            stringmember += "[]"
            self.idx_ascii += 1
        self.structstack.append(structmember)
        self.stringstack.append(stringmember)

        prefix = self.get_node_prefix(node).upper()
        curr_fp = self.curr_fp

        for field in node.fields():
            # Do not change, macro naming depends on this
            field_prefix = prefix + "__" + field.inst_name.upper()

            if field.ignore:
                curr_fp.write(
                    f"  // {field_prefix} has been ignored via injected directives\n\n"
                )
                continue

            if not field.is_sw_writable:
                curr_fp.write(f"  // {field_prefix} is software read-only\n\n")
                continue

            if not field.is_sw_readable:
                curr_fp.write(f"  // {field_prefix} is software write-only\n\n")
                continue

            if field.get_property("singlepulse"):
                curr_fp.write(f"  // {field_prefix} is singlepulse\n\n")
                continue

            self.stringstack.append(kwf(field.inst_name))

            curr_fp.write("temp_val = ")
            curr_fp.write("ReadMax32AlignedBytesFrom256(")
            curr_fp.write(
                f"reinterpret_cast<volatile __uint128_t*>(&{'.'.join(self.structstack)})"
            )
            curr_fp.write(", ")
            curr_fp.write(f"{field_prefix}_bp")
            curr_fp.write(", ")
            curr_fp.write(f"{field_prefix}_bw")
            curr_fp.write(");\n")  # function

            curr_fp.write("if(temp_val != 0) {")
            curr_fp.write("LOG_INFO(")
            curr_fp.write(f"\"{'.'.join(self.stringstack)} = %u\"")
            curr_fp.write(", ")
            curr_fp.write("temp_val")
            curr_fp.write(");")  # loginfo
            curr_fp.write("}\n")  # if
            self.stringstack.pop(-1)

        if node.ignore:
            return WalkerAction.Continue

        self.structstack.pop(-1)
        self.stringstack.pop(-1)
        if node.is_array:
            self.idx_ascii += 1
        return WalkerAction.SkipDescendants
