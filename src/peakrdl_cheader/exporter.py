import os
import subprocess
import glob
import pathlib
from typing import Any, Union

from systemrdl.node import RootNode, AddrmapNode

from .design_state import DesignState
from .design_scanner import DesignScanner
from .directive_injector import DirectiveInjector
from .nodename_retriever import NodenameRetriever
from .unique_rebuild_directive_injector import UniqueRebuildDirectiveInjector
from .csr_access_generator import CsrAccessGenerator


class CHeaderExporter:
    def export(
        self,
        node: Union[RootNode, AddrmapNode],
        directives_path: str,
        out_dir: str,
        clang_format_path: str = "",
    ) -> None:
        # If it is the root node, skip to top addrmap
        if isinstance(node, RootNode):
            top_node = node.top
        else:
            top_node = node

        ds = DesignState(top_node)

        # Validate and collect info for export
        DesignScanner(ds).run()
        print("Injecting directives...")
        DirectiveInjector(ds).run(directives_path, top_node)
        names = NodenameRetriever(ds).run(top_node)
        UniqueRebuildDirectiveInjector(ds).run(top_node, names)
        top_nodes = []
        top_nodes.append(top_node)

        # Write output

        print("Generating files...")
        CsrAccessGenerator(ds).run(out_dir, top_node)

        print("Clang-formatting files...")
        files = glob.glob(os.path.join(out_dir, "*.cc"))
        files += glob.glob(os.path.join(out_dir, "*.h"))

        try:
            for file_path in files:
                cmd = ["clang-format", "-i", file_path]
                if clang_format_path:
                    cmd = [
                        "clang-format",
                        "-i",
                        f"-style=file:{clang_format_path}",
                        file_path,
                    ]
                subprocess.run(
                    cmd,
                    check=True,
                )
        except subprocess.CalledProcessError as e:
            print(f"Error: Command failed with exit code {e.returncode}")
