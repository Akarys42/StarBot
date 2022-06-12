from starbot.bot import StarBot

BASE_ENDPOINT = "https://api.pluralkit.me/v2"
MESSAGE_ENDPOINT = BASE_ENDPOINT + "/messages/{message_id}"


async def is_deleted_by_pluralkit(bot: StarBot, message_id: int) -> bool:
    """Return true if the message has been deleted by PluralKit."""
    async with bot.aiohttp.get(MESSAGE_ENDPOINT.format(message_id=message_id)) as response:
        return response.status == 200
