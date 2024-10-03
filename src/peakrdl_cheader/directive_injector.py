import yaml
from typing import Dict, Union

from .design_state import DesignState
from systemrdl.node import Node, AddrmapNode


class DirectiveInjector:
    def __init__(self, ds: DesignState) -> None:
        self.ds = ds
        self.path: str

    def run(self, path: str, top_node: AddrmapNode) -> AddrmapNode:
        try:
            fp = open(path, "r")
            directive_data = yaml.load_all(fp, Loader=yaml.FullLoader)
            for dir_table in directive_data:
                for k, v in dir_table.items():
                    print(f"Injecting directives: {k}")
                    self.ignore_inject_recursive(top_node, v)
            fp.close()
        except FileNotFoundError:
            print(f"The file {path} was not found.")
        except Exception as e:
            print(f"An error occurred:\n{e}")

    def ignore_inject_recursive(
        self, node: Node, directives: Union[Dict, None]
    ) -> None:
        if not directives:
            node.set_ignore(True)
        else:
            for k, v in directives.items():
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
