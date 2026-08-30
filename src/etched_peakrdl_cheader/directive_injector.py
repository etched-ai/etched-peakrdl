import yaml
from typing import Dict, Union

from .design_state import DesignState
from systemrdl.node import Node, AddrmapNode, RegNode, FieldNode


class DirectiveInjector:
    def __init__(self, ds: DesignState) -> None:
        self.ds = ds
        self.path: str

    def find_field_in_regnode(self, fieldstr: str, node: RegNode) -> FieldNode:
        for field in node.fields():
            if field.inst_name == fieldstr:
                return field
        raise NameError(f"Field could not be found: {fieldstr}")

    def run(self, path: str, top_node: AddrmapNode) -> AddrmapNode:
        # Failures here must be fatal. The previous implementation wrapped the
        # whole load-and-inject sequence in `except FileNotFoundError` plus a
        # catch-all `except Exception`, printed the message, and returned
        # normally. Because ignore_inject_recursive raises NameError for every
        # directive that does not match the design (unknown node, unknown field,
        # a field given children), a single typo in the YAML aborted injection
        # part-way through and generation continued with the remaining
        # directives silently unapplied -- emitting registers and fields that the
        # directives file had explicitly marked as ignored, with nothing but one
        # line of stdout to show for it. Propagating the exception makes peakrdl
        # exit non-zero instead of shipping a wrong header.
        #
        # yaml.FullLoader is also replaced with yaml.SafeLoader. FullLoader still
        # honours tags that construct arbitrary Python objects (it only blocks
        # the subset that executes code directly), so it is not a safe parser for
        # a file that may come from another team or a generated build artifact.
        # These directives are plain nested mappings, lists, ints and strings --
        # exactly what SafeLoader supports.
        with open(path, "r", encoding="utf-8") as fp:
            for dir_table in yaml.safe_load_all(fp):
                if dir_table is None:
                    # An empty YAML document ("---" with nothing after it) is
                    # legal and carries no directives.
                    continue
                if not isinstance(dir_table, dict):
                    raise TypeError(
                        f"{path}: each directives document must be a mapping, "
                        f"got {type(dir_table).__name__}"
                    )
                for k, v in dir_table.items():
                    print(f"Injecting directives: {k}")
                    self.ignore_inject_recursive(top_node, v)
        return top_node

    def ignore_inject_recursive(
        self, node: Node, directives: Union[Dict, None]
    ) -> None:
        if not directives:
            node.set_ignore(True)
        else:
            for k, v in directives.items():
                if type(node) == RegNode:
                    if type(k) != str:
                        raise NameError(f"Regnode_insert_err: {k} not of type str")
                    if v != None:
                        raise NameError(f"field {k} cannot have children")
                    field = self.find_field_in_regnode(k, node)
                    field.set_ignore(True)

                if k == "arrayignores":
                    for basestr in v:
                        if ":" in basestr:
                            start, end = map(int, basestr.split(":"))
                            node.append_ignore_idxes(list(range(start, end)))
                        else:
                            node.append_ignore_idxes([int(basestr)])
                    continue
                recurnode = node.get_child_by_name(k)
                if not recurnode:
                    raise NameError(
                        f"Node could not be found: {k}\nAvailable: {directives.items()}"
                    )
                self.ignore_inject_recursive(recurnode, v)
        return
