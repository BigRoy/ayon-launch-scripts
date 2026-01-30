"""Launch scripts addon for AYON."""
import os
import sys

from ayon_core.addon import click_wrap, AYONAddon, IPluginPaths

from .lib import find_app_variant, print_stdout_until_timeout
from .run_script import (
    run_script as _run_script
)
from .version import __version__


class LaunchScriptsAddon(AYONAddon, IPluginPaths):
    label = "Publish Workfile"
    version = __version__
    name = "launch_scripts"

    def initialize(self, modules_settings):
        self.enabled = True

    def cli(self, click_group):
        click_group.add_command(cli_main.to_click_obj())

    def get_plugin_paths(self):
        """Implementation of IPluginPaths to get plugin paths."""
        current_dir = os.path.dirname(os.path.abspath(__file__))

        return {
            "actions": [os.path.join(current_dir,
                                     "plugins",
                                     "launcher_actions")],
        }


@click_wrap.group(LaunchScriptsAddon.name,
                  help="Publish Workfile cli commands.")
def cli_main():
    pass


@cli_main.command()
@click_wrap.option("-project", "--project_name",
                   required=True,
                   envvar="AYON_PROJECT_NAME",
                   help="Project name")
@click_wrap.option("-folder", "--folder_path",
                   required=True,
                   envvar="AYON_FOLDER_PATH",
                   help="Folder path")
@click_wrap.option("-task", "--task_name",
                   required=True,
                   envvar="AYON_TASK_NAME",
                   help="Task name")
@click_wrap.option("-path", "--filepath",
                   required=True,
                   help="Absolute filepath to workfile to publish")
@click_wrap.option("-app", "--app_name",
                   envvar="AYON_APP_NAME",
                   required=True,
                   help="App name, specific variant 'maya/2023' or just 'maya' to "
                        "take latest found variant for which current machine has "
                        "an existing executable.")
def run_script(project_name,
               folder_path,
               task_name,
               filepath,
               app_name,
               timeout=None):
    app_name = find_app_variant(app_name)
    launched_app = _run_script(
        project_name=project_name,
        folder_path=folder_path,
        task_name=task_name,
        app_name=app_name,
        script_path=filepath
    )

    print_stdout_until_timeout(launched_app, timeout, app_name)

    launched_app.wait()  # ensure we wait so that we can get the return code
    print(f"Application shut down with returncode: {launched_app.returncode}")
    sys.exit(launched_app.returncode)  # Transfer the error code


@cli_main.command()
@click_wrap.option("-project", "--project_name",
                   required=True,
                   envvar="AYON_PROJECT_NAME",
                   help="Project name")
@click_wrap.option("-folder", "--folder_path",
                   required=True,
                   envvar="AYON_FOLDER_PATH",
                   help="Folder path")
@click_wrap.option("-task", "--task_name",
                   required=True,
                   envvar="AYON_TASK_NAME",
                   help="Task name")
@click_wrap.option("-path", "--filepath",
                   required=True,
                   help="Absolute filepath to workfile to publish")
@click_wrap.option("-app", "--app_name",
                   envvar="AYON_APP_NAME",
                   required=True,
                   help="App name, specific variant 'maya/2023' or just 'maya'"
                        " to take latest found variant for which current"
                        " machine has an existing executable.")
@click_wrap.option("-prework", "--pre_workfile_script",
                   multiple=True,
                   help="Pre process script path before workfile open")
@click_wrap.option("-pre", "--pre_publish_script",
                   multiple=True,
                   help="Pre process script path")
@click_wrap.option("-post", "--post_publish_script",
                   multiple=True,
                   help="Post process script path")
@click_wrap.option("-c", "--comment",
                   help="Publish comment")
@click_wrap.option("-r", "--report-path",
                   help="Path to save publish report JSON file")
def publish(project_name,
            folder_path,
            task_name,
            filepath,
            app_name=None,
            pre_workfile_script=None,
            pre_publish_script=None,
            post_publish_script=None,
            comment=None,
            timeout=None,
            report_path=None):
    """Publish a workfile standalone for a host."""

    # The entry point should be a script that opens the workfile since the
    # `run_script` interface doesn't have an "open with file" argument due to
    # some hosts triggering scripts before opening the file or not allowing
    # both scripts to run and a file to open. As such, the best entry point
    # is to just open in the host instead and allow the script itself to open
    # a file.

    print(f"Using context {project_name} > {folder_path} > {task_name}")
    print(f"Publishing workfile: {filepath}")

    if not os.path.exists(filepath):
        raise RuntimeError(f"Filepath does not exist: {filepath}")

    # Pass specific arguments to the publish script using environment variables
    env = os.environ.copy()
    env["PUBLISH_WORKFILE"] = filepath

    # Process scripts input arguments
    for key, scripts in {
        "PUBLISH_PRE_WORKFILE_SCRIPTS": pre_workfile_script,
        "PUBLISH_PRE_SCRIPTS": pre_publish_script,
        "PUBLISH_POST_SCRIPTS": post_publish_script,
    }.items():
        script_paths = []
        for script in scripts:
            # Allow referring to locally embedded scripts with just their
            # names like e.g. `update_all_containers`
            if not os.path.isabs(script) and not script.endswith(".py"):
                script_path = os.path.join(os.path.dirname(__file__),
                                           "pre_post_scripts",
                                           f"{script}.py")
                print(f"Resolving script '{script}' as {script_path}")
                if not os.path.isfile(script_path):
                    raise FileNotFoundError(f"Script not found: {script_path}")
            else:
                script_path = script
            script_paths.append(script_path)
        env[key] = os.pathsep.join(script_paths)

    if comment:
        env["PUBLISH_COMMENT"] = comment
    if report_path:
        env["PUBLISH_REPORT_PATH"] = report_path

    script_path = os.path.join(os.path.dirname(__file__),
                               "scripts",
                               "publish_script.py")

    app_name = find_app_variant(app_name)
    launched_app = _run_script(
        project_name=project_name,
        folder_path=folder_path,
        task_name=task_name,
        app_name=app_name,
        script_path=script_path,
        env=env
    )

    print_stdout_until_timeout(launched_app, timeout, app_name)

    launched_app.wait()  # ensure we wait so that we can get the return code
    print(f"Application shut down with returncode: {launched_app.returncode}")
    sys.exit(launched_app.returncode)  # Transfer the error code
