import logging

from ayon_core.pipeline.load import get_outdated_containers
from ayon_core.pipeline import update_container

log = logging.getLogger(__name__)


def update_all_containers():
    """Update all containers in current scene to latest"""
    outdated_containers = get_outdated_containers()
    if not outdated_containers:
        print("No outdated containers found.")
        return

    for container in outdated_containers:
        name = container.get("objectName", "<no_name_>")
        print(f"Updating container: {name} | {container}")
        update_container(container, -1)


if __name__ == "__main__":
    update_all_containers()
