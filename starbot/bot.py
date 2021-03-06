import ast
import logging
import sys
from pathlib import Path
from typing import Any, Optional

import arrow
from aiohttp import ClientSession
from disnake import AllowedMentions, Game, Intents
from disnake.ext.commands import Context, InteractionBot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload, sessionmaker

from starbot.configuration.config import GuildConfig
from starbot.constants import ACI, DATABASE_URL, TEST_GUILDS
from starbot.exceptions import GuildNotConfiguredError, InDmsError
from starbot.models.guild import GuildModel

logger = logging.getLogger(__name__)


class StarBot(InteractionBot):
    """Our main bot class."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.start_time = arrow.utcnow()
        self.all_modules: list[str] = []

        self.engine = create_async_engine(DATABASE_URL)
        self.Session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self.aiohttp = ClientSession(loop=self.loop)

        self.add_app_command_check(self._is_in_dms_check, slash_commands=True)
        self.add_app_command_check(self._is_guild_configured_check, slash_commands=True)

    async def get_config(
        self, ctx_or_inter: Optional[Context | ACI] = None, *, guild_id: Optional[int] = None
    ) -> GuildConfig:
        """Retrieve the guild's configuration."""
        guild_id = guild_id or ctx_or_inter.guild.id

        async with self.Session() as session:
            guild = (
                await session.execute(
                    select(GuildModel)
                    .options(selectinload(GuildModel.config_entries))
                    .where(GuildModel.guild_id == guild_id)
                )
            ).first()

        if guild is None:
            raise GuildNotConfiguredError()

        mapped = {entry.key: entry.value for entry in guild[0].config_entries}
        return GuildConfig(guild_id, mapped)

    async def _is_guild_configured_check(self, ctx_or_inter: Context | ACI) -> bool:
        """Return whether or not the guild is configured."""
        # First check if we are bypassing the check using the
        # `starbot.decorators.bypass_guild_configured_check` decorator
        if isinstance(ctx_or_inter, ACI) and getattr(
            ctx_or_inter.application_command, "__starbot_bypass_config_check__", False
        ):
            return True

        async with self.Session() as session:
            if (
                await session.execute(
                    select(GuildModel).where(GuildModel.guild_id == ctx_or_inter.guild.id)
                )
            ).first() is None:
                raise GuildNotConfiguredError()
        return True

    async def _is_in_dms_check(self, ctx_or_inter: Context | ACI) -> bool:
        """Raises InDmsError if the command is used in DMs."""
        if ctx_or_inter.guild is None:
            raise InDmsError()
        return True

    def load_all_modules(self, module: str = "starbot.modules") -> None:
        """Find and load all modules."""
        for file in Path(module.replace(".", "/")).iterdir():
            if file.is_dir():
                self.load_all_modules(f"{module}.{file.name}")
            elif file.is_file() and file.name.endswith(".py") and not file.name.startswith("_"):
                # Check if this actually contain a module, meaning it has a setup function
                module_name = f"{module}.{file.stem}"

                try:
                    tree = ast.parse(file.read_text())

                    if any(f.name == "setup" for f in tree.body if isinstance(f, ast.FunctionDef)):
                        logger.info(f"Loading module {module_name}")
                        self.all_modules.append(module_name)
                        self.load_extension(module_name)
                except SyntaxError as e:
                    logger.error(f"{module_name} contains a syntax error:\n{e}")

    async def on_error(self, event_method: str, *args: Any, **kwargs: Any) -> None:
        """Log errors using the logging system."""
        # If the guild isn't configured or it happened in DMs, we don't want to log the error
        exception = sys.exc_info()[1]
        if isinstance(exception, (GuildNotConfiguredError, InDmsError)):
            return

        logger.exception(f"Error in {event_method!r}. Args: {args}, kwargs: {kwargs}")

    @classmethod
    def new(cls) -> "StarBot":
        """Generate a populated StarBot instance."""
        intents = Intents.all()

        intents.dm_messages = False
        intents.dm_reactions = False
        intents.dm_typing = False

        intents.presences = False
        intents.guild_typing = False
        intents.webhooks = False

        logger.debug(f"Using test guilds {TEST_GUILDS}")

        return cls(
            intents=intents,
            activity=Game(name="with slash commands!"),
            allowed_mentions=AllowedMentions(everyone=False, roles=False),
            test_guilds=TEST_GUILDS,
        )
