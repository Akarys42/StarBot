import ast
import logging
from pathlib import Path

import arrow
from disnake import AllowedMentions, Game, Intents
from disnake.ext.commands import Bot, Context
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload, sessionmaker

from starbot.configuration.config import GuildConfig
from starbot.constants import ACI, DATABASE_URL, TEST_GUILDS
from starbot.exceptions import GuildNotConfiguredError
from starbot.models.guild import GuildModel

logger = logging.getLogger(__name__)


class StarBot(Bot):
    """Our main bot class."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.start_time = arrow.utcnow()
        self.all_extensions: list[str] = []

        self.engine = create_async_engine(DATABASE_URL)
        self.Session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        self.add_app_command_check(self._is_guild_configured_check, slash_commands=True)

    async def get_config(self, ctx_or_inter: Context | ACI) -> GuildConfig:
        """Retrieve the guild's configuration."""
        async with self.Session() as session:
            guild = (
                await session.execute(
                    select(GuildModel)
                    .options(selectinload(GuildModel.config_entries))
                    .where(GuildModel.discord_id == ctx_or_inter.guild.id)
                )
            ).first()

        if guild is None:
            raise GuildNotConfiguredError()

        mapped = {entry.key: entry.value for entry in guild[0].config_entries}
        return GuildConfig(ctx_or_inter.guild.id, mapped)

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
                    select(GuildModel).where(GuildModel.discord_id == ctx_or_inter.guild.id)
                )
            ).first() is None:
                raise GuildNotConfiguredError()
        return True

    def find_extensions(self, module: str = "starbot.modules") -> None:
        """Find and load all extensions."""
        for file in Path(module.replace(".", "/")).iterdir():
            if file.is_dir():
                self.find_extensions(f"{module}.{file.name}")
            elif file.is_file() and file.name.endswith(".py") and not file.name.startswith("_"):
                # Check if this actually contain an extension, meaning it has a setup function
                module_name = f"{module}.{file.stem}"

                try:
                    tree = ast.parse(file.read_text())

                    if any(f.name == "setup" for f in tree.body if isinstance(f, ast.FunctionDef)):
                        logger.info(f"Loading extension {module_name}")
                        self.all_extensions.append(module_name)
                        self.load_extension(module_name)
                except SyntaxError as e:
                    logger.warning(f"{module_name} contains a syntax error:\n{e}")

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
            command_prefix=None,
            help_command=None,
            activity=Game(name="with slash commands!"),
            allowed_mentions=AllowedMentions(everyone=False, roles=False),
            test_guilds=TEST_GUILDS,
        )
