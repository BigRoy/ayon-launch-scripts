"""Disable review instances because they are not supported in headless maya"""
import logging

from ayon_core.pipeline.create import CreateContext, CreatedInstance
from ayon_core.pipeline import registered_host

log = logging.getLogger("maya_disable_review_instances")


def main():

    host = registered_host()
    if host.name != "maya":
        log.warning("The 'maya_disable_review_instances' script only works "
                    "with maya host. Skipping for host: %s.", host.name)
        return

    create_context = CreateContext(host)
    has_changes = False
    for instance in create_context.instances:
        instance: CreatedInstance

        # Consider only active instances
        if not instance.get("active"):
            continue

        # Consider only review insances
        if instance.get("productType") != "review":
            continue

        log.warning("Disabling review instance: %s", instance.label)
        instance["active"] = False
        has_changes = True

    if has_changes:
        log.info("Saving Create Context changes to store disabled reviews...")
        create_context.save_changes()


if __name__ == "__main__":
    main()

