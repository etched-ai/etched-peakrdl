from typing import TextIO, Set, Optional, List
import os

from treelib import Node, Tree

from systemrdl.walker import RDLListener, RDLWalker, WalkerAction
from systemrdl.node import (
    AddrmapNode,
    AddressableNode,
    RegNode,
    FieldNode,
    Node,
    MemNode,
)

from .design_state import DesignState
from .identifier_filter import kw_filter as kwf
from . import utils


class VisualizerGenerator(RDLListener):
    def __init__(self, ds: DesignState) -> None:
        self.ds = ds
        self.indent_level = 0
        self.tree = None
        self.count = 0
        self.stk = []
        self.names = {
            #     "Culpeo__MemoryMap",
            # "culpeo__MemoryMap",
            # "culpeo_zeus100n4_a_16lane__MemoryMap",
            # "culpeo_zeus100n4_a_ns_16lane__MemoryMap",
            # "DDR_CSR_APB__CPU0",
            # "hbm3cphy_inst__hbm3phy"
        }

        self.root_node: AddrmapNode
        self.root_node = None

        self.f: TextIO
        self.f = None  # type: ignore

    def run(self, top_nodes: List[AddrmapNode]) -> None:
        self.tree = Tree()
        for node in top_nodes:
            self.root_node = node
            RDLWalker().walk(node, self)
        self.tree.show(stdout=False)

    def get_node_prefix(self, node: AddressableNode) -> str:
        return utils.get_node_prefix(self.ds, self.root_node, node)

    def get_struct_name(self, node: AddressableNode) -> str:
        return utils.get_struct_name(self.ds, self.root_node, node)

    def get_friendly_name(self, node: Node) -> str:
        return utils.get_friendly_name(self.ds, self.root_node, node)

    def get_rw_test_name(self, node: Node) -> str:
        return utils.get_rw_test_name(self.ds, self.root_node, node)

    def get_namespace_name(self, node: Node) -> str:
        return utils.get_namespace_name(self.ds, self.root_node, node)

    def enter_Addrmap(self, node: AddrmapNode) -> Optional[WalkerAction]:
        nodename = f"{utils.get_struct_member_name(node)} | {utils.get_node_prefix(self.ds, self.root_node, node)} | {(node.array_dimensions[0] if node.is_array else 1)}x"
        if node.ignore or self.get_node_prefix(node) in self.names:
            return WalkerAction.SkipDescendants
        nodecnt = self.count
        self.count += 1
        if nodecnt == 0:
            self.tree.create_node(nodename, nodecnt)
        else:
            self.tree.create_node(nodename, nodecnt, parent=self.stk[-1])
        self.stk.append(nodecnt)
        for child in node.children():
            if isinstance(child, RegNode):
                return WalkerAction.SkipDescendants
        return WalkerAction.Continue

    def exit_Addrmap(self, node: AddrmapNode) -> Optional[WalkerAction]:
        nodename = self.get_node_prefix(node)
        if node.ignore or nodename in self.names:
            return WalkerAction.Continue
        self.stk.pop()
        return WalkerAction.Continue

    def enter_Reg(self, node: RegNode) -> Optional[WalkerAction]:
        return WalkerAction.SkipDescendants
