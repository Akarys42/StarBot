import ast
import logging
from pathlib import Path

import arrow
from disnake import AllowedMentions, Game, Intents
from disnake.ext.commands import Bot, when_mentioned_or

from starbot.constants import DEFAULT_PREFIX, TEST_GUILDS

logger = logging.getLogger(__name__)


class StarBot(Bot):
    """Our main bot class."""

    def __init__(self, *args, **kwargs) -> None:
        self.start_time = arrow.utcnow()
        self.all_extensions: list[str] = []
        super().__init__(*args, **kwargs)

    def find_extensions(self, module: str = "starbot.modules") -> None:
        """Find and load all extensions."""
        for file in Path(module.replace(".", "/")).iterdir():
            if file.is_dir():
                self.find_extensions(f"{module}.{file.name}")
            elif (
                file.is_file()
                and file.name.endswith(".py")
                and not file.name.startswith("_")
            ):
                # Check if this actually contain an extension, meaning it has a setup function
                module_name = f"{module}.{file.stem}"

                try:
                    tree = ast.parse(file.read_text())

                    if any(
                        f.name == "setup"
                        for f in tree.body
                        if isinstance(f, ast.FunctionDef)
                    ):
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
            command_prefix=when_mentioned_or(DEFAULT_PREFIX),
            activity=Game(name="with slash commands!"),
            case_insensitive=True,
            allowed_mentions=AllowedMentions(everyone=False, roles=False),
            test_guilds=TEST_GUILDS,
        )
