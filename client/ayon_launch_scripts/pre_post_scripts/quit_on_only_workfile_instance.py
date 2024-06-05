"""Quit with error if no active instances found other than workfile instance"""

from ayon_core.pipeline.create import CreateContext, CreatedInstance
from ayon_core.pipeline import registered_host
from ayon_core.host import IPublishHost


def main():

    host = registered_host()

    if not isinstance(host, IPublishHost):
        raise NotImplementedError(
            "Host does not support the new publisher. "
            "The 'quit on only workfile instances' script  "
            "is not supported for hosts using the legacy publisher."
        )

    # New publisher host
    create_context = CreateContext(host)

    for instance in create_context.instances:
        instance: CreatedInstance

        # Consider only active instances
        if not instance.get("active"):
            continue

        # Consider only instances that are not of workfile product type
        if instance.get("productType") == "workfile":
            continue
        if "workfile" in instance.get("families", []):
            continue

        # We have found an active instance that is not a workfile instance
        # as such, we can stop searching
        break

    else:
        # No active non-workfile instance has been found
        raise RuntimeError(
            "No active instances found in the scene that is not a Workfile "
            "instance. Exiting session."
        )


if __name__ == "__main__":
    main()
