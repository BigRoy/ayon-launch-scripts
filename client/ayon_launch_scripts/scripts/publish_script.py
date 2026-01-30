import json
import os
from pathlib import Path
import sys
import runpy

import pyblish.api
import pyblish.util
from pyblish.api import ValidatorOrder

from ayon_core.pipeline.create import CreateContext
from ayon_core.pipeline import registered_host
from ayon_core.host import IPublishHost
from ayon_core.tools.publisher.models.publish import PublishReportMaker

from ayon_launch_scripts.lib import is_success_shutdown


def run_path(path):
    """Run Python script by filepath with current globals"""
    result = runpy.run_path(path,
                            init_globals=globals(),
                            run_name='__main__')
    sys.stdout.flush()
    sys.stderr.flush()
    return result


def main():
    host = registered_host()
    assert host, "Host must already be installed and registered."

    # Get required inputs
    filepath = os.environ["PUBLISH_WORKFILE"]

    # Get optional inputs
    pre_workfile_scripts = [
        script for script in
        os.environ.get("PUBLISH_PRE_WORKFILE_SCRIPTS", "").split(os.pathsep)
        if script.strip()
    ]
    pre_publish_scripts = [
        script for script in
        os.environ.get("PUBLISH_PRE_SCRIPTS", "").split(os.pathsep)
        if script.strip()
    ]
    post_publish_scripts = [
        script for script in
        os.environ.get("PUBLISH_POST_SCRIPTS", "").split(os.pathsep)
        if script.strip()
    ]

    # TODO: What to do if a host does not auto-install? How to know which host
    #  install to trigger? Can we reliably defer maybe for all hosts?
    if not host:
        host = registered_host()
        assert host, "Must have a registered host active."

    for script in pre_workfile_scripts:
        print(f"Running pre-workfile script: {script}")
        run_path(script)
        if is_success_shutdown():
            return

    # Open workfile, the application should've been launched with the matching
    # context for that workfile
    print(f"Opening workfile: {filepath}")
    host.open_file(filepath)

    for script in pre_publish_scripts:
        print(f"Running pre-publish script: {script}")
        run_path(script)
        if is_success_shutdown():
            return

    # Trigger publish, catch errors
    success = publish()

    # Skip post-publish scripts and quit on failure
    if not success:
        sys.stdout.flush()
        sys.stderr.flush()
        _quit_application()
        raise RuntimeError("Errors occurred during publishing.")

    for script in post_publish_scripts:
        print(f"Running post-publish script: {script}")
        run_path(script)
        if is_success_shutdown():
            return

    # Force all output to be flushed
    sys.stdout.flush()
    sys.stderr.flush()


def _quit_application():
    """Force quit the host application without saving."""
    host = registered_host()

    # For Photoshop, close all documents without saving, then quit
    if getattr(host, "name", None) == "photoshop":
        try:
            from ayon_photoshop.api.launch_logic import stub
            ps_stub = stub()
            ps_stub.close_all_documents(save_changes=False)
            ps_stub.close()
        except Exception:
            pass

    # Fallback: quit Qt app
    try:
        from qtpy import QtWidgets
        app = QtWidgets.QApplication.instance()
        if app:
            app.quit()
    except Exception:
        pass


def publish():
    """Trigger headless publish in host

    Returns:
        bool: Whether publish finished successfully without errors
    """
    # Perform headless publish
    error_format = "Failed {plugin.__name__}: {error} -- {error.traceback}"

    host = registered_host()
    if isinstance(host, IPublishHost):
        # New publisher host
        create_context = CreateContext(host)

        # TODO: Allow to tweak any values on existing instances
        # if tweak_instances_fn:
        #     tweak_instances_fn(create_context.instances)
        #     create_context.save_changes()
        #     create_context.reset()

        pyblish_context = pyblish.api.Context()
        pyblish_context.data["create_context"] = create_context
        pyblish_plugins = create_context.publish_plugins
        report_maker = PublishReportMaker(
            create_context.creator_discover_result,
            create_context.convertor_discover_result,
            create_context.publish_discover_result,
        )
    else:
        # Legacy publisher host
        pyblish_context = pyblish.api.Context()  # pyblish default behavior
        pyblish_plugins = pyblish.api.discover()  # pyblish default behavior
        report_maker = None

    # Set publish comment from environment variable if provided
    comment = os.environ.get("PUBLISH_COMMENT")
    if comment:
        pyblish_context.data["comment"] = comment
        print(f"Publish comment set: {comment}")

    # Collect all validation errors instead of stopping at first one
    validation_errors = []
    current_plugin_id = None

    for result in pyblish.util.publish_iter(
            context=pyblish_context,
            plugins=pyblish_plugins
    ):
        # Print progress for the Deadline Ayon Plug-in to set the jobs
        # progress.
        if "progress" in result:
            print("Publishing Progress: {}%".format(result["progress"]))

        plugin = result.get("plugin")
        if plugin:
            for record in result["records"]:
                print("{}: {}".format(plugin.label, record.msg))
        else:
            for record in result["records"]:
                print(record.msg)

        if report_maker and plugin:
            if plugin.id != current_plugin_id:
                report_maker.add_plugin_iter(plugin.id, pyblish_context)
                current_plugin_id = plugin.id
            report_maker.add_result(plugin.id, result)
            if not result["error"]:
                report_maker.set_plugin_passed(plugin.id)

        # Handle errors
        if result["error"]:
            # Check if plugin is a Validator (order >= 1.0 and < 2.0)
            is_validator = (
                plugin and
                ValidatorOrder <= plugin.order < ValidatorOrder + 1.0
            )

            if is_validator:
                # Collect validation error, continue to run remaining validators
                validation_errors.append(result)
            else:
                # Non-validator error: stop immediately
                error_message = error_format.format(**result)
                print(error_message)
                _save_report(pyblish_context, report_maker)
                return False

    # After all plugins: check if we had validation errors
    if validation_errors:
        print("=" * 80)
        print(f"VALIDATION FAILED: {len(validation_errors)} error(s)")
        print("=" * 80)
        for idx, result in enumerate(validation_errors, 1):
            error_message = error_format.format(**result)
            print(f"  [{idx}] {error_message}")
        print("=" * 80)
        _save_report(pyblish_context, report_maker)
        return False

    _save_report(pyblish_context, report_maker)
    return True


def _save_report(pyblish_context, report_maker):
    report_path = os.environ.get("PUBLISH_REPORT_PATH")
    if not report_path or report_maker is None:
        return

    report_data = report_maker.get_report(pyblish_context)
    report_path_obj = Path(report_path)
    if (report_path_obj.exists() and report_path_obj.is_dir()) or report_path.endswith(os.sep):
        report_dir = report_path_obj
        workfile_path = os.environ.get("PUBLISH_WORKFILE", "")
        report_path_obj = report_dir / f"{Path(workfile_path).stem}_publish_report.json"
    else:
        report_dir = report_path_obj.parent
    report_dir.mkdir(parents=True, exist_ok=True)
    with open(report_path_obj, "w") as stream:
        json.dump(report_data, stream, indent=2)


if __name__ == "__main__":
    print(f"Starting publish script..")
    main()
