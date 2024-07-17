import logging
import os
import subprocess
import sys
import time
from typing import Optional

from ayon_applications import ApplicationManager
from ayon_core.pipeline import Anatomy, registered_host
from ayon_core.pipeline.context_tools import get_current_project_name
from ayon_core.pipeline.template_data import get_template_data_with_names
from ayon_core.pipeline.workfile import (
    get_workfile_template_key_from_context,
    get_last_workfile_with_version,
    get_workdir_with_workdir_data
)

log = logging.getLogger(__name__)


def get_last_workfile_for_task(
    project_name=None,
    folder_path=None,
    task_name=None,
    host_name=None,
    extensions=None
):
    """Return last existing workfile version for a task.

    Args:
        project_name (Optional[str]): Project name. Defaults to active project.
        folder_path (Optional[str]): Folder path. Defaults to AYON_FOLDER_PATH.
        task_name (Optional[str]): Task name. Defaults to AYON_TASK_NAME.
        host_name (Optional[str]): Host name. Defaults to AYON_APP_NAME.
        extensions (list): Filename extensions to look for. This defaults
            to retrieving the extensions from the currently registered host.

    Returns:
        tuple: (str: filepath, int: Version number)

    """
    # Default fallbacks
    if project_name is None:
        project_name = get_current_project_name()
    if folder_path is None:
        folder_path = os.environ["AYON_FOLDER_PATH"]
    if task_name is None:
        task_name = os.environ["AYON_TASK_NAME"]
    if host_name is None:
        host_name = os.environ["AYON_APP_NAME"]
    if extensions is None:
        host = registered_host()
        extensions = host.get_workfile_extensions()

    log.debug(
        "Searching last workfile for "
        f"{project_name} > {folder_path} > {task_name} (host: {host_name})"
    )

    template_key = get_workfile_template_key_from_context(
        project_name=project_name,
        folder_path=folder_path,
        task_name=task_name,
        host_name=host_name,
    )

    # Anatomy and workfile template data
    anatomy = Anatomy(project_name)
    data = get_template_data_with_names(
        project_name, folder_path, task_name, host_name
    )
    data["root"] = anatomy.roots

    # Work root
    work_root = get_workdir_with_workdir_data(
        workdir_data=data,
        project_name=project_name,
        anatomy=anatomy,
        template_key=template_key
    )
    log.debug(f"Looking in work root: {work_root}")

    # Filename
    file_template = anatomy.get_template_item("work", template_key, "file")
    filename, version = get_last_workfile_with_version(
        work_root, str(file_template), data, extensions
    )

    # Full path
    if filename:
        filename = os.path.join(work_root, filename)

    return filename, version


def find_app_variant(app_name, application_manager=None):
    """Searches for relevant application.

    If app_name equals e.g. `maya` or `houdini` it will try to retrieve
    the latest version available on the local machine.

    If app equals e.g. `maya/2023` or `houdini/19.0.435` (exact key for app
    variant) then it will try and launch that application.

    Arguments:
        application_manager (ApplicationManager)
        app_name (str): Name of host or full application name, e.g.
            "maya" or "maya/2023"

    Returns:
        str: Application group / variant name

    Raises:
        ValueError: if no valid application variant found
    """

    if application_manager is None:
        application_manager = ApplicationManager()

    if "/" in app_name:
        host, variant_key = app_name.split("/", 1)
    else:
        host = app_name
        variant_key = None

    app_group = application_manager.app_groups.get(host)
    if not app_group or not app_group.enabled:
        raise ValueError("No application {} configured".format(host))

    if not variant_key:
        # finds most up-to-date variant if any installed
        # TODO: This should actually be filtered by the project settings too
        #  so it only allows to retrieve Application version enabled in
        #  the project!
        variant = (
            application_manager.find_latest_available_variant_for_group(host)
        )
        if not variant:
            raise ValueError("No executable for {} found".format(host))
        variant_key = variant.name
    else:
        # ensure the requested version is available on this machine
        if variant_key not in app_group.variants:
            raise ValueError(
                "Variant {} not found amongst variants: {}".format(
                    variant_key, ", ".join(app_group.variants.keys())
                )
            )

        # Detect if executables exist
        for executable in app_group.variants[variant_key].executables:
            if executable.exists():
                break
        else:
            raise ValueError("No executable for {} found".format(app_name))

    return f"{host}/{variant_key}"


def print_stdout_until_timeout(
    popen: subprocess.Popen, timeout: Optional[float] = None, app_name: str = None
):
    """Print stdout until app close.

    If app remains open for longer than `timeout` then app is terminated.

    """
    time_start = time.time()
    prefix = f"{app_name}: " if app_name else " "
    default_encoding = sys.getdefaultencoding()

    for line in popen.stdout:
        # Print stdout, remove windows carriage return and decode according to system encoding

        line = line.replace(b"\r", b"")
        line_str = line.decode(default_encoding, errors="ignore")
        print(f"{prefix}{line_str}", end="")

        if timeout and time.time() - time_start > timeout:
            popen.terminate()
            raise RuntimeError("Timeout reached")
