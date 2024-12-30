"""Quit with an error if there are no outdated containers found"""
from ayon_core.pipeline.load import any_outdated_containers

from ayon_launch_scripts import lib

if __name__ == "__main__":
    if not any_outdated_containers():
        lib.succeed_with_message(
            "No outdated containers found in the scene, as such there is "
            "nothing to update and nothing new to publish. Exiting session."
        )
