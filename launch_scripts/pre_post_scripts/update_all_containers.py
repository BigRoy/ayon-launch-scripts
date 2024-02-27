from collections import defaultdict
import logging

from openpype.pipeline import registered_host

from openpype.client import get_representations, version_is_latest
from openpype.pipeline.context_tools import get_current_project
from openpype.pipeline import update_container

log = logging.getLogger(__name__)


def update_all_containers():
    """Update all containers in current scene to latest"""
    host = registered_host()

    containers_by_repre_ids = defaultdict(list)

    for container in host.get_containers():
        representation_id = container.get("representation")
        if not representation_id:
            continue

        containers_by_repre_ids[representation_id].append(container)

    if not containers_by_repre_ids:
        print("No containers in scene.")
        return

    project = get_current_project(fields=["name"])
    project_name = project["name"]

    representations = get_representations(
        project_name=project_name,
        representation_ids=list(containers_by_repre_ids.keys())
    )
    outdated_ids = {
        str(repre["_id"]) for repre in representations
        if not version_is_latest(project_name, repre["parent"])
    }
    if not outdated_ids:
        print("No outdated containers found.")
        return

    for repre_id, containers in containers_by_repre_ids.items():
        if repre_id not in outdated_ids:
            continue

        print(f"Updating outdated containers for representation: {repre_id}")
        for container in containers:
            print(f"Updating container: {container}")
            update_container(container, -1)


if __name__ == "__main__":
    update_all_containers()
