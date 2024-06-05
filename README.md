### AYON Addon Launch Script

This defines a module/addon for [AYON](https://ayon.ynput.io/) which exposes a command line 
interface to run Python scripts within support host applications like Blender,
Maya, Houdini and Fusion.

_It's like AYON has gone headless!_

### Installation

Create the AYON addon package using the `create_package.py` script similar to other AYON addons:
```
python ./create_package.py
```

Upload the addon package to your AYON server and add it to your bundle.

### Examples

#### Running a headless script

When currently inside an environment that has the OpenPype context environment
variables for `AYON_FOLDER_PATH`, `AYON_TASK_NAME`, etc. you can just run:

```shell
ayon_console addon launch_scripts run-script -app maya/2023 -path /path/to/script.py
```

But in most case you'll need to explicitly provide the context you want to run
the script in:
```shell
ayon_console addon launch_scriptsrun-script 
-project my_project
-folder /asset/char_hero
-task modeling
-app maya/2023 
-path /path/to/script.py
```
_The arguments are on new-lines here solely for readability. They are arguments
to the same command and should usually be on a single line._

#### Running a headless publish

The module also exposes a `publish` command. Usable like so:

```shell
ayon_console addon launch_scriptspublish
-project my_project
-folder /asset/char_hero
-task modeling
-app maya/2023 
-path /path/to/workfile.ma
```

This will launch the host headless, then open the workfile and publish as usual.


#### Default context

It will pass along these defaults from environment variables if you
do not explicitly pass the relevant command line arguments:
- `-project`: `AYON_PROJECT_NAME`
- `-folder_path`: `AYON_FOLDER_PATH`
- `-task`: `AYON_TASK_NAME`
- `-host`: `AYON_APP_NAME`

### Remarks

- **Script input arguments:** To supply specific input arguments to your scripts it's recommended to supply
environment variables to the launched application and retrieve them in your script
from `os.environ` since not all hosts supported passing along custom additional arguments unrelated to its launch.

### Supported applications

For each supported host an entry point needs to be created so headless scripts
can run against it. Currently only the following hosts are supported:

- Blender: ok
- Fusion: only in gui mode, does not suppress prompts nor exits at the end
- Houdini: ok
- Maya: ok - _note that playblasting and thus publishing reviews is not supported in Maya headless mode_
- Nuke: implemented but untested (includes Nuke X and Nuke Studio)

### Running against source code

Instead of running `ayon_console addon` you can also run AYON launcher in dev mode: `ayon-launcher/tools/ayon_console.bat --use-dev addon launch_scripts`. 

As such an example usage against run code could look like:

```shell
ayon-launcher/tools/ayon_console.bat --use-dev addon launch_scripts publish
-project my_project
-folder /asset/char_hero
-task modeling
-app maya/2023 
-path /path/to/workfile.ma
```
