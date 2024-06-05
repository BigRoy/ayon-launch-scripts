import logging

from maya import cmds


def force_delete(node):
    if cmds.objExists(node):
        cmds.lockNode(node, lock=False)
        cmds.delete(node)


def remove_unknown_plugin(plugin):
    log = logging.getLogger("remove_unknown_plugin")

    log.info("Removing unknown plugin: %s .." % plugin)

    for node in cmds.ls(type="unknown"):
        if not cmds.objExists(node):
            # Might have been deleted in previous iteration
            log.info("Already deleted: {}".format(node))
            continue

        if cmds.unknownNode(node, query=True, plugin=True) != plugin:
            continue

        nodetype = cmds.unknownNode(node,
                                    query=True,
                                    realClassName=True)
        log.info("Deleting unknown node {} "
                 "(original type: {})".format(node, nodetype))

        try:
            force_delete(node)
        except RuntimeError as exc:
            log.error(exc)

    # TODO: Remove datatypes
    # datatypes = cmds.unknownPlugin(plugin,
    #                                query=True, dataTypes=True)
    try:
        cmds.unknownPlugin(plugin, remove=True)
    except RuntimeError as exc:
        log.warning(
            "Failed to remove plug-in {}: {}".format(plugin, exc)
        )


def remove_unknown_plugins(ignore=None):
    plugins = sorted(cmds.unknownPlugin(query=True, list=True) or [])

    # Ignore specific plug-ins allowed to be unknown
    if ignore:
        plugins = [plugin for plugin in plugins if plugin not in ignore]

    for plugin in plugins:
        remove_unknown_plugin(plugin)


if __name__ == "__main__":
    # Remove unknown plugins
    remove_unknown_plugins(ignore={"stereoCamera"})
