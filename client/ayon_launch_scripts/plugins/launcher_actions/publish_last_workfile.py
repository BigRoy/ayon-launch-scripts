import os
import platform
import logging
from json import JSONDecodeError
from typing import Optional

from ayon_core.lib import get_ayon_username
from ayon_core.settings import get_project_settings
from ayon_core.pipeline.context_tools import get_current_project_name
from ayon_applications import (
    Application,
    ApplicationManager
)
from ayon_core.pipeline.actions import LauncherActionSelection
from ayon_applications.utils import (
    get_app_icon_path,
    get_applications_for_context,
)
from ayon_core.pipeline import LauncherAction
from ayon_core.tools.utils.lib import get_qt_icon
from ayon_core.style import load_stylesheet

from qtpy import QtGui, QtCore, QtWidgets

log = logging.getLogger(__name__)


def get_application_qt_icon(application: Application) -> Optional[QtGui.QIcon]:
    """Return QtGui.QIcon for an Application"""
    icon = application.icon
    if not icon:
        return QtGui.QIcon()
    icon_filepath = get_app_icon_path(icon)
    if os.path.exists(icon_filepath):
        return get_qt_icon({"type": "path", "path": icon_filepath})
    return QtGui.QIcon()


def submit_to_deadline(
        job_info: dict,
        plugin_info: dict,
        aux_files: list = None
):
    if aux_files is None:
        aux_files = []

    # Some keys to always transfer into the Deadline job if the local
    # environment has them. So we submit them along to Deadline as
    # environment key values in the Job's info.
    keys = [
        "FTRACK_API_KEY",
        "FTRACK_API_USER",
        "FTRACK_SERVER",
        "OPENPYPE_SG_USER"
    ]
    env = {}
    for key in keys:
        if key in os.environ:
            env[key] = os.environ[key]
    for index, (key, value) in enumerate(env.items()):
        job_info[f"EnvironmentKeyValue{index}"] = f"{key}={value}"

    payload = {
        "JobInfo": job_info,
        "PluginInfo": plugin_info,
        "AuxFiles": aux_files
    }
    return submit_payload_to_deadline(payload)


def submit_payload_to_deadline(payload: dict) -> str:
    """Submit payload to Deadline API end-point.

    This takes payload in the form of JSON file and POST it to
    Deadline jobs end-point.

    Args:
        payload (dict): dict to become json in deadline submission.

    Returns:
        str: resulting Deadline job id.

    Throws:
        KnownPublishError: if submission fails.

    """
    from ayon_deadline.abstract_submit_deadline import requests_post

    # Use default url
    project_name = get_current_project_name()
    project_settings = get_project_settings(project_name)
    deadline_urls = project_settings["deadline"]["deadline_urls"]

    # TODO: Do not force the 'default' entry
    # TODO: Support the authentication and verify ssl logic of settings
    deadline_url = next(
        deadline_info["value"] for deadline_info in deadline_urls
        if deadline_info["name"] == "default"
    )

    url = "{}/api/jobs".format(deadline_url)

    response = requests_post(url, json=payload)
    if not response.ok:
        log.error("Submission failed!")
        log.error(response.status_code)
        log.error(response.content)
        log.debug(payload)
        raise RuntimeError(response.text)

    try:
        result = response.json()
    except JSONDecodeError:
        msg = "Broken response {}. ".format(response)
        msg += "Try restarting the Deadline Webservice."
        log.warning(msg, exc_info=True)
        raise RuntimeError("Broken response from DL")

    return result["_id"]


class PublishLastWorkfile(LauncherAction):
    """
    Submit a job to deadline that will open the workfile, update all containers
    and trigger a headless publish on the farm.
    """
    name = "publishlastworkfile"
    label = "Publish"
    icon = "rocket"
    color = "#ffffff"
    order = 20

    def is_compatible(self, selection) -> bool:
        return selection.is_task_selected

    def process(self, selection, **kwargs):
        import ayon_launch_scripts.lib
        import importlib
        importlib.reload(ayon_launch_scripts.lib)
        from ayon_launch_scripts.lib import get_last_workfile_for_task

        pos = QtGui.QCursor.pos()

        # Get the environment
        project_name = selection.get_project_name()
        folder_path = selection.get_folder_path()
        task_name = selection.get_task_name()

        # Get applications
        application_manager = ApplicationManager()
        applications = self.get_project_applications(
            application_manager, selection)
        app = self.choose_app(applications, pos)
        if not app:
            return

        app_name = app.full_name

        # TODO: Do not hardcode this here - access them from the hosts, but
        #  we currently cannot access those from outside the hosts/applications
        extensions = {
            "houdini": [".hip"],
            "maya": [".ma", ".mb"],
            "fusion": [".comp"]
        }[app.host_name]

        # Find latest workfile with `AVALON_SCENEDIR` support
        workfile, version_number = get_last_workfile_for_task(
            project_name=project_name,
            folder_path=folder_path,
            task_name=task_name,
            host_name=app.host_name,
            extensions=extensions
        )
        if not workfile:
            raise RuntimeError("No existing workfile found.")

        args = [
            "addon",
            "launch_scripts",
            "publish",
            "--project_name", project_name,
            "--folder_path", folder_path,
            "--task_name", task_name,
            "--app_name", str(app.full_name),
            "--filepath", workfile
        ]

        # TODO: Remove the hardcoded scripts and replace it with a simple
        #   GUI the artist can use to decide what to do
        if app.host_name == "maya":
            args.extend(["-prework", "maya_load_alembic_plugin"])   # fix AbcImport being reported as unknown plugin
        args.extend(["-pre", "quit_on_no_outdated"])                # do nothing if scene has no outdated content
        args.extend(["-pre", "update_all_containers"])              # always update all containers
        if app.host_name == "maya":
            args.extend(["-pre", "maya_disable_review_instances"])  # headless review publishing doesn't work in maya - lets ignore those
        args.extend(["-pre", "quit_on_only_workfile_instance"])     # do not publish if only workfile instance is active
        args.extend(["-pre", "print_instances"])                    # print os.environ

        # Define some labeling
        batch_name = f"{project_name} | Publish workfiles"
        filename = os.path.basename(workfile)
        name = f"{folder_path} > {task_name} > {app_name} | {filename}"

        submit_to_deadline(
            job_info={
                "Plugin": "Ayon",
                "BatchName": batch_name,
                "Name": name,
                "UserName": get_ayon_username(),
                "MachineName": platform.node(),

                # Error out early on this job since it's unlikely
                # a subsequent publish will suddenly succeed and
                # this avoids trying to create tons of publishes
                "OverrideJobFailureDetection": True,
                "FailureDetectionJobErrors": 3
            },
            plugin_info={
                "Version": "3.0",
                "Arguments": " ".join(args),
                "SingleFrameOnly": "True",
            }
        )

    @staticmethod
    def choose_app(
        applications: list[Application],
        pos: QtCore.QPoint,
        show_variant_name_only: bool = False
    ) -> Optional[Application]:
        """Show menu to choose from list of applications"""
        menu = QtWidgets.QMenu()
        menu.setAttribute(QtCore.Qt.WA_DeleteOnClose)  # force garbage collect
        menu.setStyleSheet(load_stylesheet())

        # Sort applications
        applications.sort(key=lambda item: item.full_label)

        for app in applications:
            label = app.label if show_variant_name_only else app.full_label
            menu_action = QtWidgets.QAction(label, parent=menu)
            icon = get_application_qt_icon(app)
            if icon:
                menu_action.setIcon(icon)
            menu_action.setData(app)
            menu.addAction(menu_action)

        result = menu.exec_(pos)
        if result:
            return result.data()

    @staticmethod
    def get_project_applications(
            application_manager: ApplicationManager,
            selection: LauncherActionSelection) -> list[Application]:
        """Return the enabled applications for the project"""

        application_names = get_applications_for_context(
            project_name=selection.project_name,
            folder_entity=selection.folder_entity,
            task_entity=selection.task_entity,
            project_settings=selection.get_project_settings(),
            project_entity=selection.project_entity
        )

        # Filter to apps valid for this current project, with logic from:
        # `ayon_core.tools.launcher.models.actions.ApplicationAction.is_compatible`  # noqa
        applications = []
        for app_name in application_names:
            app = application_manager.applications.get(app_name)
            if not app or not app.enabled:
                continue
            applications.append(app)

        return applications
