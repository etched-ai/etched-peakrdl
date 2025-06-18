from typing import Optional, Set

from systemrdl.walker import RDLListener, RDLWalker, WalkerAction
from systemrdl.node import AddrmapNode, AddressableNode, RegNode, RegfileNode, FieldNode, Node, MemNode

from .design_state import DesignState
from . import utils

class UniqueRebuildDirectiveInjector(RDLListener):
    def __init__(self, ds: DesignState) -> None:
        self.ds = ds
        self.root_node: AddrmapNode
        self.names: Set[str]

    def get_node_prefix(self, node: AddressableNode) -> str:
        return utils.get_node_prefix(self.ds, self.root_node, node)

    def run(self, root_node:AddrmapNode, names:Set[str]) -> Set[str]:
        self.root_node = root_node
        self.names = names
        RDLWalker().walk(root_node, self)

    def get_node_prefix(self, node: AddressableNode) -> str:
        return utils.get_node_prefix(self.ds, self.root_node, node)

    def enter_Addrmap(self, node: AddrmapNode) -> Optional[WalkerAction]:
        if(self.get_node_prefix(node) in self.names):
            node.set_unique(False)
        else:
            return WalkerAction.Continue
        childstk = list(node.children())
        while childstk:
            child = childstk.pop(0)
            if(child.ignore):
                node.set_rebuild(True)
                return WalkerAction.Continue
            if type(child) is RegfileNode:
                childstk = list(child.children()) + childstk
        return WalkerAction.Continue

    def enter_Reg(self, node: RegNode) -> Optional[WalkerAction]:
        return WalkerAction.SkipDescendants

    def enter_Regfile(self, node: RegfileNode) -> Optional[WalkerAction]:
        return WalkerAction.SkipDescendants