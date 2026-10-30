
import inspect
from pathlib import Path


# Generated helper modules contain exactly two
# infrastructure lines before the GUI source.
ADDITIONAL_FILE_HEADER_LINES = 2


def get_developer_error_location(
    exc,
    view_func,
    api_version,
):
    """
    Return a developer-GUI-relative error location.

    Supports:
    - Dynamically generated views
    - Additional developer Python files

    Returns None when no matching developer
    source location can be identified.
    """

    if view_func is None:
        return None

    original_view = inspect.unwrap(view_func)

    view_code = getattr(
        original_view,
        "__code__",
        None,
    )

    if view_code is None:
        return None

    gui_start_line = getattr(
        original_view,
        "__api_gui_start_line__",
        None,
    )

    gui_source = getattr(
        original_view,
        "__api_gui_source__",
        None,
    )

    # The loader must return the generated view,
    # with its source metadata attached.
    if gui_start_line is None or gui_source is None:
        return None

    view_source_lines = gui_source.split("\n")

    # Locate the generated views module directory.
    generated_views_path = Path(
        view_code.co_filename
    ).resolve()

    dynamic_app_directory = (
        generated_views_path.parent
    )

    # Build a lookup for valid developer helper files.
    additional_sources = {}

    reserved_names = {
        "__init__.py",
        "models.py",
        "views.py",
        "urls.py",
    }

    for file in api_version.version_files or []:
        if not isinstance(file, dict):
            continue

        filename = file.get("name")
        content = file.get("content")

        if (
            not isinstance(filename, str)
            or not isinstance(content, str)
            or Path(filename).name != filename
            or "/" in filename
            or "\\" in filename
            or not filename.endswith(".py")
            or filename in reserved_names
            or not filename[:-3].isidentifier()
        ):
            continue

        full_path = (
            dynamic_app_directory / filename
        ).resolve()

        additional_sources[full_path] = (
            filename,
            content.split("\n"),
        )

    # Walk all traceback frames.
    tb = exc.__traceback__
    location = None

    while tb is not None:
        frame = tb.tb_frame
        python_line = tb.tb_lineno

        # Case A: Exact dynamically generated view.
        if frame.f_code is view_code:

            gui_line = (
                python_line - gui_start_line + 1
            )

            if 1 <= gui_line <= len(view_source_lines):
                location = {
                    "file": "views.py",
                    "line": gui_line,
                    "function": view_code.co_name,
                    "code": (
                        view_source_lines[
                            gui_line - 1
                        ].strip()
                    ),
                }

        else:
            # Case B: Developer's additional file.
            frame_path = Path(
                frame.f_code.co_filename
            ).resolve()

            source = additional_sources.get(
                frame_path
            )

            if source is not None:
                filename, source_lines = source

                gui_line = (
                    python_line
                    - ADDITIONAL_FILE_HEADER_LINES
                )

                if 1 <= gui_line <= len(source_lines):
                    location = {
                        "file": filename,
                        "line": gui_line,
                        "function": frame.f_code.co_name,
                        "code": (
                            source_lines[
                                gui_line - 1
                            ].strip()
                        ),
                    }

        tb = tb.tb_next

    return location
