import logging

import coloredlogs

from starbot.bot import StarBot
from starbot.constants import TOKEN


def main() -> None:
    """Prepare the bot and start it."""
    coloredlogs.install(level="DEBUG")

    logging.getLogger("disnake").setLevel(logging.WARNING)
    logging.getLogger("charset_normalizer").setLevel(logging.WARNING)

    bot = StarBot.new()

    logging.info("Loading extensions")
    bot.find_extensions()

    logging.info("Starting bot")
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
