"""Print instances"""

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

    create_context = CreateContext(host)
    for instance in create_context.instances:
        instance: CreatedInstance

        if instance.get("active"):
            print(f"Publishing instance: {instance.label}")
        else:
            print(f"Skipping inactive instance: {instance.label}")


if __name__ == "__main__":
    main()
