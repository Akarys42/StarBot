import asyncio
import functools
from types import FunctionType
from typing import Callable
from weakref import WeakValueDictionary

Decorator = Callable[[FunctionType], FunctionType]


def argument_lock(arg_index: int) -> Decorator:
    """Decorator locking the function to the given argument index."""

    def decorator(func: FunctionType) -> FunctionType:
        __locks = WeakValueDictionary()

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> None:
            __lock_key = args[arg_index]
            __lock = __locks.setdefault(__lock_key, asyncio.Lock())

            async with __lock:
                return await func(*args, **kwargs)

        return wrapper

    return decorator
