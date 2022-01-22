import logging

from disnake.ext.commands import Cog, slash_command

from starbot.bot import StarBot
from starbot.constants import ACI

RED_CIRCLE = "\N{LARGE RED CIRCLE}"
GREEN_CIRCLE = "\N{LARGE GREEN CIRCLE}"


logger = logging.getLogger(__name__)


class ExtensionManagement(Cog):
    """List, enable, and disable extensions."""

    def __init__(self, bot: StarBot) -> None:
        self.bot = bot
        super().__init__()

    async def cog_slash_command_check(self, inter: ACI) -> bool:
        """Check that the user is one of the owner."""
        return await self.bot.is_owner(inter.author)

    def _list_extension_status(self) -> list[tuple[str, bool]]:
        """Return a list of tuples of extension name and whenever they are loaded or not."""
        loaded = self.bot.extensions.keys()
        return [(ext, ext in loaded) for ext in self.bot.all_extensions]

    def _get_extension_status(self, ext: str) -> bool:
        """Return whether the extension is loaded or not."""
        return ext in self.bot.extensions.keys()

    @slash_command()
    async def exts(self, inter: ACI) -> None:
        """Manage loaded extensions."""
        pass

    @exts.sub_command(name="list")
    async def list_(self, inter: ACI) -> None:
        """List all the extensions and their status."""
        lines = [
            f"{RED_CIRCLE if not loaded else GREEN_CIRCLE} `{ext}`"
            for ext, loaded in self._list_extension_status()
        ]
        await inter.send("\n".join(lines))

    @exts.sub_command()
    async def load(self, inter: ACI, ext: str) -> None:
        """Load an extension."""
        if self._get_extension_status(ext):
            await inter.send(f":x: extension `{ext}` is already loaded.")
            return

        try:
            self.bot.load_extension(ext)
            logger.info(f"Manually loaded extension {ext}.")
        except Exception as e:
            await inter.send(f":x: Failed to load extension `{ext}`: {e}")
            return

        await inter.send(f":white_check_mark: extension `{ext}` loaded.")

    @exts.sub_command()
    async def unload(self, inter: ACI, ext: str) -> None:
        """Unload an extension."""
        if not self._get_extension_status(ext):
            await inter.send(f":x: extension `{ext}` is not loaded.")
            return

        try:
            self.bot.unload_extension(ext)
            logger.info(f"Manually unloaded extension {ext}.")
        except Exception as e:
            await inter.send(f":x: Failed to unload extension `{ext}`: {e}")
            return

        await inter.send(f":white_check_mark: extension `{ext}` unloaded.")

    @exts.sub_command()
    async def reload(self, inter: ACI, ext: str) -> None:
        """Reload an extension."""
        if not self._get_extension_status(ext):
            await inter.send(f":x: extension `{ext}` is not loaded.")
            return

        try:
            self.bot.reload_extension(ext)
            logger.info(f"Manually reloaded extension {ext}.")
        except Exception as e:
            await inter.send(f":x: Failed to reload extension `{ext}`: {e}")
            return

        await inter.send(f":white_check_mark: extension `{ext}` reloaded.")

    @load.autocomplete("ext")
    def load_autocomplete(self, _inter: ACI, query: str) -> list[str]:
        """Autocomplete for the load command."""
        return [
            ext
            for ext, status in self._list_extension_status()
            if query in ext and not status
        ]

    @unload.autocomplete("ext")
    def unload_autocomplete(self, _inter: ACI, query: str) -> list[str]:
        """Autocomplete for the unload command."""
        return [
            ext
            for ext, status in self._list_extension_status()
            if query in ext and status
        ]

    @reload.autocomplete("ext")
    def reload_autocomplete(self, _inter: ACI, query: str) -> list[str]:
        """Autocomplete for the reload command."""
        return [
            ext
            for ext, status in self._list_extension_status()
            if query in ext and status
        ]


def setup(bot: StarBot) -> None:
    """Load the extension."""
    bot.add_cog(ExtensionManagement(bot))
