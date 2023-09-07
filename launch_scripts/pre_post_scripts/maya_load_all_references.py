

def main():
    """Load all unloaded references"""
    from maya import cmds

    for ref_path in cmds.file(query=True, reference=True):
        if not cmds.referenceQuery(ref_path, isLoaded=True):
            print(f"Loading unloaded reference: {ref_path}")
            cmds.file(ref_path, loadReference=True)
