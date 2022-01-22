from disnake import AllowedMentions, Game, Intents
from disnake.ext.commands import Bot, when_mentioned_or

from starbot.constants import DEFAULT_PREFIX


class StarBot(Bot):
    """Our main bot class."""

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

        return cls(
            intents=intents,
            command_prefix=when_mentioned_or(DEFAULT_PREFIX),
            activity=Game(name="with slash commands!"),
            case_insensitive=True,
            allowed_mentions=AllowedMentions(everyone=False, roles=False),
        )
