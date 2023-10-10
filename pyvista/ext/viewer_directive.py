"""Viewer directive module."""
import os
import pathlib
import shutil
import sys

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.utils import relative_path  # pragma: no cover
from sphinx.util import logging
from trame_vtk.tools.vtksz2html import HTML_VIEWER_PATH

logger = logging.getLogger(__name__)


def is_path_relative_to(path, other):
    """Path.is_relative_to was introduced in Python 3.9 [1].
    Provide a replacement that works for all supported versions

    [1] https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.is_relative_to
    """
    if sys.version_info < (3, 9):
        path = str(path.resolve())
        other = str(other.resolve())
        return path.startswith(other)
    else:  # pragma: no cover
        return path.is_relative_to(other)


class OfflineViewerDirective(Directive):
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    has_content = True

    def run(self):  # pragma: no cover
        source_dir = pathlib.Path(self.state.document.settings.env.app.srcdir)
        output_dir = pathlib.Path(self.state.document.settings.env.app.outdir)
        # _build directory
        build_dir = pathlib.Path(self.state.document.settings.env.app.outdir).parent

        # this is the path passed to 'offlineviewer:: <path>` directive
        source_file = os.path.join(
            os.path.dirname(self.state.document.current_source), self.arguments[0]
        )
        source_file = pathlib.Path(source_file).absolute().resolve()
        if not os.path.isfile(source_file):
            logger.warn(f'Source file {source_file} does not exist.')
            return []

        # copy viewer HTML to _static
        static_path = pathlib.Path(output_dir) / '_static'
        static_path.mkdir(exist_ok=True)
        if not pathlib.Path(static_path, os.path.basename(HTML_VIEWER_PATH)).exists():
            shutil.copy(HTML_VIEWER_PATH, static_path)

        # calculate the scene asset path relative to the build directory and
        # recreate the directory structure under output_dir/_images. This
        # avoids overriding files with the same name e.g. index-x_yy_zz.vtksz will
        # be generated by any index.rst file and we have a number of them.
        # Example:
        # source_file ${HOME}/pyvista/pyvista/doc/_build/plot_directive/getting-started/index-2_00_00.vtksz
        # dest_partial_path: plot_directive/getting-started
        # dest_path: ${HOME}/pyvista/pyvista/doc/_build/html/_images/plot_directive/getting-started/index-2_00_00.vtksz

        if is_path_relative_to(source_file, build_dir):
            dest_partial_path = pathlib.Path(source_file.parent).relative_to(build_dir)
        elif is_path_relative_to(source_file, source_dir):
            dest_partial_path = pathlib.Path(source_file.parent).relative_to(source_dir)
        else:
            logger.warn(
                f'Source file {source_file} is not a subpath of either the build directory of the source directory. Cannot extarct base path'
            )
            return []

        dest_path = pathlib.Path(output_dir).joinpath('_images').joinpath(dest_partial_path)
        dest_path.mkdir(parents=True, exist_ok=True)
        dest_file = dest_path.joinpath(source_file.name).resolve()
        if source_file != dest_file:
            try:
                shutil.copy(source_file, dest_file)
            except Exception as e:
                logger.warn(f'Failed to copy file from {source_file} to {dest_file}: {e}')

        # Compute the relative path of the current source to the source directory,
        # which is the same as the relative path of the '_static' directory to the
        # generated HTML file.
        relpath_to_source_root = relative_path(self.state.document.current_source, source_dir)
        rel_viewer_path = (
            pathlib.Path(".")
            / relpath_to_source_root
            / '_static'
            / os.path.basename(HTML_VIEWER_PATH)
        ).as_posix()
        rel_asset_path = pathlib.Path(os.path.relpath(dest_file, static_path)).as_posix()
        html = f"""
    <iframe src='{rel_viewer_path}?fileURL={rel_asset_path}' width='100%%' height='400px' frameborder='0'></iframe>
"""

        raw_node = nodes.raw('', html, format='html')

        return [raw_node]


def setup(app):
    app.add_directive('offlineviewer', OfflineViewerDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
