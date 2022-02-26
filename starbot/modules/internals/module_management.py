import logging

from disnake.ext.commands import Cog, slash_command

from starbot.bot import StarBot
from starbot.constants import ACI
from starbot.decorators import bypass_guild_configured_check

RED_CIRCLE = "\N{LARGE RED CIRCLE}"
GREEN_CIRCLE = "\N{LARGE GREEN CIRCLE}"


logger = logging.getLogger(__name__)


class ModuleManagement(Cog):
    """List, enable, and disable modules."""

    def __init__(self, bot: StarBot) -> None:
        self.bot = bot
        super().__init__()

    async def cog_slash_command_check(self, inter: ACI) -> bool:
        """Check that the user is one of the owners."""
        return await self.bot.is_owner(inter.author)

    def _list_module_status(self) -> list[tuple[str, bool]]:
        """Return a list of tuples of module name and whenever they are loaded or not."""
        loaded = self.bot.extensions.keys()
        return [(mod, mod in loaded) for mod in self.bot.all_modules]

    def _get_module_status(self, mod: str) -> bool:
        """Return whether the module is loaded or not."""
        return mod in self.bot.extensions.keys()

    @bypass_guild_configured_check
    @slash_command()
    async def modules(self, inter: ACI) -> None:
        """Manage loaded modules."""
        pass

    @bypass_guild_configured_check
    @modules.sub_command(name="list")
    async def list_(self, inter: ACI) -> None:
        """List all the modules and their status."""
        lines = [
            f"{RED_CIRCLE if not loaded else GREEN_CIRCLE} `{mod}`"
            for mod, loaded in self._list_module_status()
        ]
        await inter.send("\n".join(lines))

    @bypass_guild_configured_check
    @modules.sub_command()
    async def load(self, inter: ACI, mod: str) -> None:
        """Load a module."""
        if self._get_module_status(mod):
            await inter.send(f":x: module `{mod}` is already loaded.")
            return

        try:
            self.bot.load_extension(mod)
            logger.info(f"Manually loaded module {mod}.")
        except Exception as e:
            await inter.send(f":x: Failed to load module `{mod}`: {e}")
            logger.exception(f"Failed to load module `{mod}`.")
            return

        await inter.send(f":white_check_mark: module `{mod}` loaded.")

    @bypass_guild_configured_check
    @modules.sub_command()
    async def unload(self, inter: ACI, mod: str) -> None:
        """Unload a module."""
        if not self._get_module_status(mod):
            await inter.send(f":x: module `{mod}` is not loaded.")
            return

        try:
            self.bot.unload_extension(mod)
            logger.info(f"Manually unloaded module {mod}.")
        except Exception as e:
            await inter.send(f":x: Failed to unload module `{mod}`: {e}")
            logger.exception(f"Failed to unload module `{mod}`.")
            return

        await inter.send(f":white_check_mark: module `{mod}` unloaded.")

    @bypass_guild_configured_check
    @modules.sub_command()
    async def reload(self, inter: ACI, mod: str) -> None:
        """Reload a module."""
        if not self._get_module_status(mod):
            await inter.send(f":x: module `{mod}` is not loaded.")
            return

        try:
            self.bot.reload_extension(mod)
            logger.info(f"Manually reloaded module {mod}.")
        except Exception as e:
            await inter.send(f":x: Failed to reload module `{mod}`: {e}")
            logger.exception(f"Failed to reload module `{mod}`.")
            return

        await inter.send(f":white_check_mark: module `{mod}` reloaded.")

    @load.autocomplete("mod")
    def load_autocomplete(self, _inter: ACI, query: str) -> list[str]:
        """Autocomplete for the load command."""
        return [mod for mod, status in self._list_module_status() if query in mod and not status]

    @unload.autocomplete("mod")
    def unload_autocomplete(self, _inter: ACI, query: str) -> list[str]:
        """Autocomplete for the unload command."""
        return [mod for mod, status in self._list_module_status() if query in mod and status]

    @reload.autocomplete("mod")
    def reload_autocomplete(self, _inter: ACI, query: str) -> list[str]:
        """Autocomplete for the reload command."""
        return [mod for mod, status in self._list_module_status() if query in mod and status]


def setup(bot: StarBot) -> None:
    """Load the module."""
    bot.add_cog(ModuleManagement(bot))
