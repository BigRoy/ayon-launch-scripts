### OpenPype Addon: Launch Script

This defines a module/addon for OpenPype which exposes  a command line 
interface to run Python scripts within support host applications like Blender,
Maya, Houdini and Fusion.

### Installation

To install make sure the root is a discoverable path for OpenPype modules in
in your studio. This can be configured in **Studio Settings > System > Modules > OpenPype Addon Paths** (`modules/addon_paths`).

### Examples

#### Running a headless script

When currently inside an environment that has the OpenPype context environment
variables for `AVALON_ASSET`, `AVALON_TASK`, etc. you can just run:

```shell
openpype_console module launch_scripts run-script -app maya/2023 -path /path/to/script.py
```

But in most case you'll need to explicitly provide the context you want to run
the script in:
```shell
openpype_console module launch_scripts run-script 
-project my_project
-asset hero
-task modeling
-app maya/2023 
-path /path/to/script.py
```
_The arguments are on new-lines here solely for readability. They are arguments
to the same command and should usually be one a single line._

#### Running a headless publish

The module also exposes a `publish` command. Usable like so:

```shell
openpype_console module launch_scripts publish
-project my_project
-asset hero
-task modeling
-app maya/2023 
-path /path/to/workfile.ma
```

This will launch the host headless, then open the workfile and publish as usual.


#### Default context

It will pass along these defaults from environment variables if you
do not explicitly pass the relevant command line arguments:
- `-project`: `AVALON_PROJECT`
- `-asset`: `AVALON_ASSET`
- `-task`: `AVALON_TASK`
- `-host`: `AVALON_APP_NAME`

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

Instead of running `openpype_console module` you can also run `.poetry\bin\poetry run python start.py module`. As such an example usage against run code could look like:

```shell
.poetry\bin\poetry run python start.py module launch_scripts publish
-project my_project
-asset hero
-task modeling
-app maya/2023 
-path /path/to/workfile.ma
```
