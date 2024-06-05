
from maya import cmds


# If Alembic is not loaded before the workfile opens it may be reported
# as an unknown plug-in. So we ensure to load now.
cmds.loadPlugin("AbcImport", quiet=True)
cmds.loadPlugin("AbcExport", quiet=True)
