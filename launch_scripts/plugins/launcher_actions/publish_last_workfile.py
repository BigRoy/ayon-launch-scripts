import os
import platform
import logging
from json import JSONDecodeError
from typing import Optional, Tuple, Dict

from openpype.pipeline import LauncherAction
from openpype.client import get_project
from openpype.lib import (
    ApplicationManager,
    get_openpype_username
)
from openpype.settings import get_system_settings
from openpype.lib.applications import (
    Application,
    get_app_environments_for_context,
)

log = logging.getLogger(__name__)


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
    from openpype_modules.deadline.abstract_submit_deadline import requests_post

    # Use default url
    system_settings = get_system_settings()
    deadline_url = (
        system_settings["modules"]["deadline"]["deadline_urls"]["default"]
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

    def is_compatible(self, session: dict):
        required = {"AVALON_PROJECT", "AVALON_ASSET", "AVALON_TASK"}
        return all(session.get(key) for key in required)

    def process(self, session: dict, **kwargs):
        from openpype_modules.launch_scripts.lib import get_last_workfile_for_task

        # Get the environment
        project_name = session["AVALON_PROJECT"]
        asset_name = session["AVALON_ASSET"]
        task_name = session["AVALON_TASK"]

        applications = self.get_applications(project_name)
        result = self.choose_app(applications)
        if not result:
            return

        app_name, app = result
        app: Application

        # TODO: Do not hardcode this here - access them from the hosts, but
        #  we currently cannot access those from outside the hosts/applications
        extensions = {
            "houdini": [".hip"],
            "maya": [".ma", ".mb"],
            "fusion": [".comp"]
        }[app.host_name]

        # Find latest workfile with `AVALON_SCENEDIR` support
        env = get_app_environments_for_context(project_name,
                                               asset_name,
                                               task_name,
                                               app_name)
        scene_dir = env.get("AVALON_SCENEDIR")
        workfile, version_number = get_last_workfile_for_task(
            project_name=project_name,
            asset_name=asset_name,
            task_name=task_name,
            host_name=app.host_name,
            scene_dir=scene_dir,
            extensions=extensions
        )
        if not workfile:
            raise RuntimeError("No existing workfile found.")

        args = [
            "module",
            "launch_scripts",
            "publish",
            "--project_name", project_name,
            "--asset_name", asset_name,
            "--task_name", task_name,
            "--app_name", str(app.full_name),
            "--filepath", workfile
        ]

        # TODO: Remove the hardcoded scripts and replace it with a simple
        #   GUI the artist can use to decide what to do
        # Always update containers first
        args.extend(["-pre", "update_all_containers"])

        # Define some labeling
        batch_name = f"{project_name} | Publish workfiles"
        filename = os.path.basename(workfile)
        name = f"{asset_name} > {task_name} > {app_name} | {filename}"

        submit_to_deadline(
            job_info={
                "Plugin": "OpenPype",
                "BatchName": batch_name,
                "Name": name,
                "UserName": get_openpype_username(),
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
            applications: Dict[str, Application]
    ) -> Optional[Tuple[str, Application]]:
        import openpype.style
        from qtpy import QtWidgets, QtGui
        from openpype.tools.launcher.lib import get_action_icon

        menu = QtWidgets.QMenu()
        menu.setStyleSheet(openpype.style.load_stylesheet())

        # Sort applications
        applications = sorted(
            applications.items(),
            key=lambda item: item[1].name
        )

        for app_name, app in applications:
            label = f"{app.group.label} {app.label}"
            icon = get_action_icon(app)

            menu_action = QtWidgets.QAction(label, parent=menu)
            if icon:
                menu_action.setIcon(icon)
            menu_action.setData((app_name, app))
            menu.addAction(menu_action)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            return result.data()

    @staticmethod
    def get_applications(project_name: str) -> Dict[str, Application]:

        # Get applications
        manager = ApplicationManager()
        manager.refresh()

        # Create mongo connection
        project_doc = get_project(project_name)
        assert project_doc, "Project not found. This is a bug."

        # Filter to apps valid for this current project, with logic from:
        # `openpype.tools.launcher.models.ActionModel.get_application_actions`
        applications = {}
        for app_def in project_doc["config"]["apps"]:
            app_name = app_def["name"]
            app = manager.applications.get(app_name)
            if not app or not app.enabled:
                continue
            applications[app_name] = app

        return applications
