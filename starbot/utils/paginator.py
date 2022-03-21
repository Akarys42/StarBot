import inspect
import logging
from typing import AsyncIterator, Iterator, Optional

from disnake import Button, ButtonStyle, Embed, MessageInteraction
from disnake.ui import View, button

from starbot.constants import ACI

DISCORD_EMBED_LIMIT = 4096

PREV = "\N{LEFTWARDS BOTTOM-SHADED WHITE ARROW}"
NEXT = "\N{RIGHTWARDS BOTTOM SHADED WHITE ARROW}"


logger = logging.getLogger(__name__)


class PaginatorView(View):
    """
    View used to paginate a list of items.

    Supports lazily fetching of items from a generator.
    """

    def __init__(
        self,
        *args,
        inter: ACI = None,
        gen: list[str] | Iterator[str] | AsyncIterator[str] | None = None,
        color: int = 0,
        title: Optional[str] = None,
        separator: str = "\n\n",
        max_len: int = DISCORD_EMBED_LIMIT,
        **kwargs,
    ) -> None:
        if gen is None:
            raise ValueError("PaginatorView requires a generator.")

        super().__init__(*args, **kwargs)

        self.inter = inter
        self.gen = gen
        self.color = color
        self.max_len = max_len
        self.title = title
        self.separator = separator

        self.page_cache = []
        self.item_cache = []
        self.current_page = -1

    async def start(self) -> None:
        """Start the paginator."""
        content = await self.get_page(0)

        if content is None:
            return

        embed = Embed(description=content, color=self.color)
        embed.set_footer(text="Page 1")

        if self.title is not None:
            embed.title = self.title

        self.current_page = 0

        await self.inter.send(embed=embed, view=self)

    async def _fetch_item(self) -> bool:
        """
        Fetch an item from the generator and add it to the cache.

        Returns True if an item was fetched, False otherwise.
        """
        try:
            if isinstance(self.gen, list):
                self.item_cache.append(self.gen.pop(0))
            elif inspect.isasyncgen(self.gen):
                self.item_cache.append(await self.gen.__anext__())
            elif inspect.isgenerator(self.gen):
                self.item_cache.append(self.gen.__next__())
            else:
                raise TypeError(
                    "PaginatorView generator must be a list, async iterator, or iterator."
                )
        except (StopIteration, IndexError):
            return False

        return True

    async def get_page(self, page: int) -> Optional[str]:
        """
        Return the page at that index.

        Returns None if the page is out of bounds.
        """
        if page < 0:
            return None

        while len(self.page_cache) <= page:
            page_full = True

            while (
                sum(len(item) for item in self.item_cache)
                + len(self.separator) * (len(self.item_cache) - 1)
                < self.max_len
            ):
                has_new_item = await self._fetch_item()

                if not has_new_item:
                    page_full = False
                    break

            # We have no more items to make a page.
            if not self.item_cache:
                logger.debug("No more items to paginate.")
                self.page_cache.append(None)
                return

            # We have enough items to make a page.
            if page_full:
                # To not go above the page limit, we need to remove the last item.
                self.page_cache.append(self.separator.join(self.item_cache[:-1]))
                self.item_cache = self.item_cache[-1:]
            else:
                # We have reached the end of the generator.
                self.page_cache.append(self.separator.join(self.item_cache))
                self.item_cache = []

        return self.page_cache[page]

    async def display_page(self, page: int) -> None:
        """Display the page at that index."""
        content = await self.get_page(page)

        if content is None:
            return

        embed = Embed(description=content, color=self.color)
        embed.set_footer(text=f"Page {page + 1}")

        if self.title is not None:
            embed.title = self.title

        await self.inter.edit_original_message(embed=embed, view=self)
        self.current_page = page

    async def interaction_check(self, interaction: MessageInteraction) -> bool:
        """Check if the interaction author is the paginator's author."""
        return interaction.author.id == self.inter.author.id

    @button(label=PREV, style=ButtonStyle.gray)
    async def previous_page(self, button_: Button, interaction: MessageInteraction) -> None:
        """Display the previous page."""
        await interaction.response.defer()
        await self.display_page(self.current_page - 1)

    @button(label=NEXT, style=ButtonStyle.gray)
    async def next_page(self, button_: Button, interaction: MessageInteraction) -> None:
        """Display the next page."""
        await interaction.response.defer()
        await self.display_page(self.current_page + 1)
