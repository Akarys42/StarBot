import logging

import coloredlogs

from starbot.bot import StarBot
from starbot.constants import GIT_SHA, LOGGING_LEVEL, TOKEN


def main() -> None:
    """Prepare the bot and start it."""
    coloredlogs.install(level=LOGGING_LEVEL)

    logging.getLogger("disnake").setLevel(logging.WARNING)
    logging.getLogger("charset_normalizer").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)

    bot = StarBot.new()

    logging.info("Loading extensions")
    bot.find_extensions()

    logging.info(f"Starting bot, build {GIT_SHA}")
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
