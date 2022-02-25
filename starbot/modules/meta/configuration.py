from io import StringIO

import yaml
from aiohttp import ClientError
from disnake import File, Permissions, TextChannel, Thread
from disnake.ext.commands import Cog, slash_command
from sqlalchemy import and_, delete, select

from starbot.bot import StarBot
from starbot.checks import is_guild_owner, require_permission
from starbot.configuration.definition import DEFINITION
from starbot.configuration.utils import config_to_tree, get_dotted_path
from starbot.constants import ACI
from starbot.decorators import bypass_guild_configured_check, multi_autocomplete
from starbot.models import ConfigEntryModel, GuildModel

CONFIGURED_MESSAGE = """
:white_check_mark: This server has been configured!
You can now use the `/config` command to adjust the configuration.

We recommend you to set the following entries:
- `logging.channels.default`: The channel where the bot will log various Discord events.
""".strip()


class Configuration(Cog):
    """A cog for managing the per guild configuration of the bot."""

    def __init__(self, bot: StarBot) -> None:
        self.bot = bot
        self.autocomplete_fields = {}

        self._populate_autocomplete_fields()

    def _populate_autocomplete_fields(self, path: str = "") -> None:
        """Populate the autocomplete fields starting from `path`."""
        for key, value in get_dotted_path(DEFINITION, path).items():
            new_path = f"{path}.{key}" if path else key

            assert isinstance(value, dict)
            if "type" in value:
                self.autocomplete_fields[f"{value['description']} ({new_path})"] = new_path
            else:
                self._populate_autocomplete_fields(new_path)

    @bypass_guild_configured_check
    @slash_command()
    async def config(self, ctx: ACI) -> None:
        """Configure the bot for your guild."""
        pass

    @require_permission(role_id="config.perms.role", permissions="config.perms.discord")
    @config.sub_command()
    async def set(self, inter: ACI, key: str, value: str) -> None:
        """Set a configuration key to a value."""
        # Check if the key is valid
        if not (definition := get_dotted_path(DEFINITION, key)):
            await inter.send(":x: Invalid configuration key.", ephemeral=True)
            return

        # Check if the value is valid
        config = await self.bot.get_config(inter)
        try:
            config.convert_entry(value, definition)
        except ValueError:
            await inter.send(":x: Invalid value.", ephemeral=True)
            return

        async with self.bot.Session() as session:
            # See if this config key exists.
            query = select(ConfigEntryModel).where(
                and_(ConfigEntryModel.key == key, ConfigEntryModel.guild_id == inter.guild.id)
            )
            entry = (await session.execute(query)).first()

            if entry is None:
                # If it doesn't, create it.
                entry = ConfigEntryModel(key=key, value=value, guild_id=inter.guild.id)
                session.add(entry)
            else:
                # If it does, update it.
                entry[0].value = value
            await session.commit()
        await inter.send(f":white_check_mark: Configuration updated: `{key}` set to `{value}`.")

    @require_permission(role_id="config.perms.role", permissions="config.perms.discord")
    @config.sub_command()
    async def get(self, inter: ACI, key: str) -> None:
        """Get the value of a configuration key."""
        # Check if the key is valid
        if not (definition := get_dotted_path(DEFINITION, key)):
            await inter.send(":x: Invalid configuration key.", ephemeral=True)
            return

        # Check if the key is set or not
        async with self.bot.Session() as session:
            query = select(ConfigEntryModel).where(
                and_(ConfigEntryModel.key == key, ConfigEntryModel.guild_id == inter.guild.id)
            )
            entry = (await session.execute(query)).first()

            if entry is None:
                message = (
                    f"Configuration key `{key}` isn't set. Default value: `{definition['default']}`"
                )
            else:
                message = f"Configuration key `{key}`: `{entry[0].value}`"

        await inter.send(message)

    @require_permission(role_id="config.perms.role", permissions="config.perms.discord")
    @config.sub_command()
    async def reset(self, inter: ACI, key: str) -> None:
        """Reset a configuration key to its default value."""
        # Check if the key is valid
        if not (definition := get_dotted_path(DEFINITION, key)):
            await inter.send(":x: Invalid configuration key.", ephemeral=True)
            return

        async with self.bot.Session() as session:
            query = delete(ConfigEntryModel).where(
                and_(ConfigEntryModel.key == key, ConfigEntryModel.guild_id == inter.guild.id)
            )
            rowcount = (await session.execute(query)).rowcount

            if rowcount == 0:
                await inter.send(
                    f":x: The default value for `{key}` is already set: `{definition['default']}`.",
                    ephemeral=True,
                )
            else:
                await session.commit()
                await inter.send(
                    f":white_check_mark: Configuration reset: `{key}` reset "
                    f"to `{definition['default']}`."
                )

    @set.autocomplete("value")
    async def set_value_autocomplete(self, inter: ACI, value: str) -> dict[str, str] | list[str]:
        """
        Tries to autocomplete the value based on the configuration key type.

        Due to a Discord limitation we have to echo the parameter back to the user
        if we don't have any special handling for that type.
        """
        key = inter.options["set"]["key"]

        if not (definition := get_dotted_path(DEFINITION, key)):
            return ["Invalid configuration key."]

        match definition["type"]:
            case "discord_role":
                roles = {}

                for role in inter.guild.roles or await inter.guild.fetch_roles():
                    if len(roles) >= 25:
                        break

                    if value.lower() in f"{role.name} ({role.id})".lower():
                        roles[f"{role.name} ({role.id})"] = str(role.id)
                return roles
            case "discord_channel":
                channels = {}

                for channel in inter.guild.channels or await inter.guild.fetch_channels():
                    if len(channels) >= 25:
                        break

                    if (
                        isinstance(channel, (TextChannel, Thread))
                        and value.lower() in f"#{channel.name} ({channel.id})".lower()
                    ):
                        channels[f"#{channel.name} ({channel.id})"] = str(channel.id)
                return channels
            case "discord_permission":
                perms = {}

                for name, _ in Permissions():
                    if len(perms) >= 25:
                        break

                    if value.lower().replace(" ", "_") in name:
                        perms[name.replace("_", " ").capitalize()] = name

                return perms
            case "bool":
                return ["True", "False"]
            case "choice":
                return [choice for choice in definition["choices"] if value in choice][:25]
            case _:
                return [value or " "]  # Need to return something else than an empty string

    @require_permission(role_id="config.perms.role", permissions="config.perms.discord")
    @config.sub_command("import")
    async def import_(self, inter: ACI, url: str) -> None:
        """
        Import a configuration from a URL.

         Warning: This will overwrite your current configuration.
        """
        try:
            async with self.bot.aiohttp.get(url) as resp:
                resp.raise_for_status()

                config = yaml.safe_load(await resp.text())
        except ClientError:
            await inter.send(":x: Invalid URL.", ephemeral=True)
            return
        except yaml.YAMLError:
            await inter.send(":x: Invalid YAML.", ephemeral=True)
            return

        if not isinstance(config, dict):
            await inter.send(":x: Invalid configuration.", ephemeral=True)
            return

        # Drop existing config
        async with self.bot.Session() as session:
            query = delete(ConfigEntryModel).where(ConfigEntryModel.guild_id == inter.guild.id)
            await session.execute(query)

            added = 0
            ignored = 0
            invalid = 0

            # Import new config
            nodes = [(config, "")]
            while nodes:
                node, path = nodes.pop()

                for key, value in node.items():
                    new_path = f"{path}.{key}" if path else key

                    # If the value is a dict, add it to the stack
                    if isinstance(value, dict):
                        nodes.append((value, new_path))
                    # Otherwise check the key is valid and add it to the database
                    else:
                        definition = get_dotted_path(DEFINITION, new_path)
                        if not definition:
                            invalid += 1
                            continue

                        try:
                            (await self.bot.get_config(inter)).convert_entry(value, definition)
                        except ValueError:
                            invalid += 1
                            continue

                        if value == definition["default"]:
                            ignored += 1
                            continue

                        entry = ConfigEntryModel(
                            key=new_path, value=str(value), guild_id=inter.guild.id
                        )
                        session.add(entry)
                        added += 1

            await session.commit()
            await inter.send(
                f":white_check_mark: Configuration imported: {added} entries added, "
                f"{ignored} ignored, {invalid} invalid."
            )

    @require_permission(role_id="config.perms.role", permissions="config.perms.discord")
    @config.sub_command()
    async def export(self, inter: ACI, include_defaults: bool = False) -> None:
        """Upload the configuration as a YAML file."""
        config = await self.bot.get_config(inter)
        tree = config_to_tree(config, include_defaults=include_defaults)

        file = StringIO()
        yaml.dump(tree, file)
        file.seek(0)

        await inter.send(
            "Configuration uploaded as an attachment", file=File(file, "configuration.yaml")
        )

    @multi_autocomplete((set, "key"), (get, "key"), (reset, "key"))
    async def set_key_autocomplete(self, inter: ACI, prefix: str) -> dict[str, str] | list[str]:
        """Autocomplete the configuration key."""
        # If we have just a dot, we return raw keys
        if prefix == ".":
            return list(self.autocomplete_fields.values())

        # If it is a valid path, we return direct paths
        if "." in prefix and " " not in prefix:
            return [
                value for value in self.autocomplete_fields.values() if value.startswith(prefix)
            ]

        # Otherwise we match both the description and the path
        return {key: value for key, value in self.autocomplete_fields.items() if prefix in key}

    @bypass_guild_configured_check
    @is_guild_owner()
    @config.sub_command()
    async def setup(self, inter: ACI) -> None:
        """Bootstrap the bot."""
        async with self.bot.Session() as session:
            # Check if the guild isn't already configured
            if (
                await session.execute(
                    select(GuildModel).where(GuildModel.guild_id == inter.guild.id)
                )
            ).first() is not None:
                await inter.send(":x: This guild is already configured.", ephemeral=True)
                return

            guild = GuildModel(guild_id=inter.guild.id)

            session.add(guild)
            await session.commit()

        await inter.send(CONFIGURED_MESSAGE)


def setup(bot: StarBot) -> None:
    """Load the Configuration cog."""
    bot.add_cog(Configuration(bot))
