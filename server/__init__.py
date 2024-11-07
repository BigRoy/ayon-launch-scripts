from typing import Type

from ayon_server.addons import BaseServerAddon

from .settings import LaunchScriptsSettings, DEFAULT_VALUES


class LaunchScriptsAddon(BaseServerAddon):
    name = "launch_scripts"
    title = "Launch Scripts"
    settings_model: Type[LaunchScriptsSettings] = LaunchScriptsSettings

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_VALUES)
