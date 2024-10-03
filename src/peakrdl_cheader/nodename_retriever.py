from typing import Optional, Set

from systemrdl.walker import RDLListener, RDLWalker, WalkerAction
from systemrdl.node import AddrmapNode, AddressableNode, RegNode, RegfileNode, FieldNode, Node, MemNode

from .design_state import DesignState
from . import utils

class NodenameRetriever(RDLListener):
    def __init__(self, ds: DesignState) -> None:
        self.ds = ds
        self.root_node: AddrmapNode
        self.names = set()
        self.uniquenames = set()

    def get_node_prefix(self, node: AddressableNode) -> str:
        return utils.get_node_prefix(self.ds, self.root_node, node)
    
    def run(self, root_node:AddrmapNode) -> Set[str]:
        self.root_node = root_node
        RDLWalker().walk(root_node, self)
        return self.uniquenames

    def enter_Addrmap(self, node: AddrmapNode) -> Optional[WalkerAction]:
        if(self.get_node_prefix(node) in self.names):
            self.uniquenames.add(self.get_node_prefix(node))
        self.names.add(self.get_node_prefix(node))
    
    def enter_Reg(self, node: RegNode) -> Optional[WalkerAction]:
        return WalkerAction.SkipDescendants

    def enter_Regfile(self, node: RegfileNode) -> Optional[WalkerAction]:
        return WalkerAction.SkipDescendants