from typing import Generator, List
import logging

from maya import cmds

log = logging.getLogger(__name__)


def iter_instances() -> Generator[str]:
    """Yield publish instances object sets in scene"""
    for objset in cmds.ls("*.id", type="objectSet", objectsOnly=True,
                          long=True):
        if cmds.getAttr(f"{objset}.id") != "pyblish.avalon.instance":
            continue
        if not cmds.attributeQuery("productType", node=objset, exists=True):
            continue

        yield objset


def get_nodes_with_childtype(nodes: List[str], childtype: str) -> List[str]:
    """Return nodes that have a particular node type as child"""
    if not nodes:
        return []
    children = cmds.listRelatives(nodes, children=True, type=childtype,
                                  fullPath=True) or []
    if not children:
        return []
    return cmds.listRelatives(children, parent=True, fullPath=True) or []


def clean_camera_instances():
    """Remove image planes from cameras"""

    for objset in iter_instances():
        if cmds.getAttr(f"{objset}.productType") != "camera":
            continue

        members = cmds.sets(objset, query=True)

        cameras = get_nodes_with_childtype(members, childtype="camera")
        camera_children = cmds.listRelatives(cameras, children=True,
                                             fullPath=True) or []
        image_planes = get_nodes_with_childtype(camera_children,
                                                childtype="imagePlane")
        if image_planes:
            print(f"Deleting image planes: {image_planes}")
            cmds.delete(image_planes)


if __name__ == "__main__":
    clean_camera_instances()
