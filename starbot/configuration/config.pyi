# flake8: noqa
# This file is automatically generated by tools/generate_config_typing.py
# Do not modify this file directly.
# The content of this file is based on the config-definition.yaml file.
# It is used to provide type hints for the config module, to be used by your IDE.

# fmt: off

from typing import Optional

import disnake

from starbot.configuration.config_abc import ConfigABC

class GuildConfig(ConfigABC):

    class bot(ConfigABC):
        info_channel: Optional[int]
        description: str

    class logging(ConfigABC):

        class channels(ConfigABC):
            default: Optional[int]
            moderation: Optional[int]
            messages: Optional[int]
            members: Optional[int]
            joins: Optional[int]
            server: Optional[int]

    class moderation(ConfigABC):

        class perms(ConfigABC):
            role: Optional[int]
            discord: Optional[disnake.Permissions]

        class messages(ConfigABC):
            dm_description: Optional[optional:str]

    class config(ConfigABC):

        class perms(ConfigABC):
            role: Optional[int]
            discord: Optional[disnake.Permissions]

    class phishing(ConfigABC):
        should_filter: bool
        action: str
        dm: str
        bypass_permission: disnake.Permissions

    class colors(ConfigABC):
        danger: int
        warning: int
        info: int
        success: int
