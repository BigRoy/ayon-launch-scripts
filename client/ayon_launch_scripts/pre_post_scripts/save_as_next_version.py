"""Save the current workfile to AYON work directory with proper versioning.

Intended to be used as a pre-publish script (--pre_publish_script save_as_next_version)
so it runs after the workfile is opened. Saves the document to the AYON workfile path
with the next version number.
"""
from ayon_core.pipeline import registered_host
from ayon_core.pipeline.workfile.utils import save_next_version


def main():
    print("Saving workfile to AYON work directory with proper versioning...")
    try:
        save_next_version()
        host = registered_host()
        saved_path = host.get_current_workfile()
        if saved_path:
            print(f"Successfully saved workfile to: {saved_path}")
        else:
            print("Warning: Workfile saved but could not retrieve saved path")
    except Exception as e:
        print(f"ERROR: Failed to save workfile: {e}")
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Failed to save workfile to AYON work directory: {e}")


if __name__ == "__main__":
    main()
