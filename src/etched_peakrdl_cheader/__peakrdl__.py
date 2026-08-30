from typing import TYPE_CHECKING

from peakrdl.plugins.exporter import ExporterSubcommandPlugin #pylint: disable=import-error

from .exporter import CHeaderExporter

if TYPE_CHECKING:
    import argparse
    from systemrdl.node import AddrmapNode


class Exporter(ExporterSubcommandPlugin):
    short_desc = "Generate Etched CSR access sources for an address space"

    # CHeaderExporter.export() writes several files (one .h/.cc pair per top
    # block, plus the visualizer output) into a directory, so -o names a
    # directory rather than a single file. Leaving this at the framework default
    # of True would make peakrdl treat -o as a file path and pass it straight
    # through, which is not what the exporter expects.
    generates_output_file = False

    # This fork's DesignState hardcodes the C standard, typedef style, bitfield
    # packing order and sub-word size (see design_state.py), so there is nothing
    # for a config file to select. The upstream peakrdl-cheader schema entries
    # ("std", "type_style", "subword_size", "bitfields") were retained here long
    # after the exporter stopped reading them; keeping them would advertise
    # configuration that silently has no effect, so the schema is empty.
    cfg_schema = {}

    def add_exporter_arguments(self, arg_group: 'argparse._ActionsContainer') -> None:
        arg_group.add_argument(
            "--directives",
            dest="directives_path",
            required=True,
            help="""
            Path to the YAML directives file that annotates the design with the
            per-node generation directives this exporter consumes. Required:
            CHeaderExporter.export() has no default for it.
            """
        )

        arg_group.add_argument(
            "--clang-format-path",
            dest="clang_format_path",
            default="",
            help="""
            Path to a .clang-format style file. When given, generated sources are
            formatted with "clang-format -style=file:<path>". When omitted,
            clang-format runs with its own default style resolution.
            """
        )

    def do_export(self, top_node: 'AddrmapNode', options: 'argparse.Namespace') -> None:
        # Keyword names must track exporter.py's signature exactly. The previous
        # version of this method still passed the upstream peakrdl-cheader
        # arguments (path=, std=, generate_bitfields=, bitfield_order_ltoh=,
        # reuse_typedefs=, wide_reg_subword_size=, explode_top=, instantiate=,
        # inst_offset=, testcase=), none of which this fork's export() accepts.
        # Every CLI invocation therefore died with a TypeError before any output
        # was produced; the plugin entry point was completely unusable.
        exporter = CHeaderExporter()
        exporter.export(
            top_node,
            directives_path=options.directives_path,
            out_dir=options.output,
            clang_format_path=options.clang_format_path,
        )
