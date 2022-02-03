import json
import logging
import re
from contextlib import suppress
from string import Template

import websockets
from disnake import Forbidden, Member, Message, NotFound
from disnake.ext.commands import Cog

from starbot.bot import StarBot
from starbot.constants import DEBUG, GIT_SHA

# Scam list API
from starbot.exceptions import GuildNotConfiguredError

API_ALL = "https://phish.sinking.yachts/v2/all"
API_WS = "wss://phish.sinking.yachts/feed"

# Domain regex
DOMAIN_REGEX = re.compile(r"(?i)\b((?:[a-z0-9][-a-z0-9]*[a-z0-9]\.)+[a-z][-a-z0-9]{0,22}[a-z0])")

# Useful formatting links
LINK_PASSWORD = (
    "https://support.discord.com/hc/en-us/articles/"
    "218410947-I-forgot-my-Password-Where-can-I-set-a-new-one"
)
LINK_2FA = (
    "https://support.discord.com/hc/en-us/articles/219576828-Setting-up-Two-Factor-Authentication"
)


logger = logging.getLogger(__name__)


class Phishing(Cog):
    """
    Detects and take action against phishing links.

    Relies on the SinkingYachts API.
    """

    def __init__(self, bot: StarBot) -> None:
        self.bot = bot
        self.domains: set[str] = set()
        self.ready = False
        self.headers = {"X-Identity": f"StarBot {self.bot.user} {GIT_SHA[:6]}"}

        self.bot.loop.create_task(self.consume_feed())

        if not DEBUG:
            self.bot.loop.create_task(self.populate_domains())
        else:
            logger.warning(
                "Phishing link detection disabled in debug mode. Adding scam.com to the list."
            )
            self.ready = True
            self.domains = {"scam.com"}

    async def populate_domains(self) -> None:
        """Populates the links set with phishing links."""
        logger.debug("Populating phishing links...")
        self.domains = set()

        async with self.bot.aiohttp.get(API_ALL, headers=self.headers) as resp:
            data = await resp.json()

            for link in data:
                self.domains.add(link)

        self.ready = True
        logger.info("Phishing link detection ready.")

    async def consume_feed(self) -> None:
        """Connect to the domain feed and wait for changes."""
        async with websockets.connect(API_WS, extra_headers=self.headers) as ws:
            async for message in ws:
                data = json.loads(message)

                match data["type"]:
                    case "add":
                        function = self.domains.add
                    case "delete":
                        function = self.domains.discard
                    case _:
                        logger.warning(f"Unknown message type: {data['type']}")
                        continue

                logger.debug(
                    f"{data['type'].rstrip('e')}ing {data['domains']} from the domain list"
                )

                for domain in data["domains"]:
                    function(domain)

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        """Find phishing links in messages."""
        try:
            config = await self.bot.get_config(guild_id=message.guild.id)
        except GuildNotConfiguredError:
            return

        if not self.ready or not config.phishing.should_filter:
            return

        if message.author.bot:
            return

        for match in DOMAIN_REGEX.finditer(message.content):
            domain = match.group(0)

            if domain in self.domains:
                logger.debug(f"Detected phishing link {domain!r} from {message.author}.")

                if message.channel.permissions_for(message.author).is_superset(
                    config.phishing.bypass_permission
                ):
                    logger.debug(f"{message.author} will bypass the filter.")

                    with suppress(Forbidden):
                        await message.add_reaction("\N{WARNING SIGN}")

                    return

                with suppress(NotFound, Forbidden):
                    await message.delete()

                match config.phishing.action:
                    case "ban":
                        action = f"You have been banned from {message.guild.name}."
                    case "kick":
                        action = f"You have been kicked from {message.guild.name}."
                    case "ignore":
                        action = ""
                    case _:
                        logger.error(f"Invalid phishing action {config.phishing.action}.")
                        return

                dm_message = Template(config.phishing.dm).safe_substitute(
                    user=str(message.author),
                    action=action,
                    LINK_PASSWORD=LINK_PASSWORD,
                    LINK_2FA=LINK_2FA,
                )

                with suppress(NotFound, Forbidden):
                    await message.author.send(dm_message)

                with suppress(Forbidden):
                    if isinstance(message.author, Member):
                        match config.phishing.action:
                            case "ban":
                                await message.author.ban(reason="Phishing link sent.")
                            case "kick":
                                await message.author.kick(reason="Phishing link sent.")
                            case "ignore":
                                pass

                break


def setup(bot: StarBot) -> None:
    """Loads the Phishing cog."""
    bot.add_cog(Phishing(bot))
