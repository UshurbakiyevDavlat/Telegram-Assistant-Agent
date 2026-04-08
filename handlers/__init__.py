"""
Root router — aggregates all feature routers.
Order matters: commands are checked first, then personal chat.
"""
from typing import Final

from aiogram import Router

from .commands import commands_router
from .group import group_router
from .personal import personal_router

root_router: Final[Router] = Router(name="root")

# Register routers — order matters:
# 1. Commands first (/start, /clear, /help)
# 2. Group chat (responds only on @mention or reply)
# 3. Personal chat (catches all remaining text in private DMs)
root_router.include_routers(
    commands_router,
    group_router,
    personal_router,
)

__all__ = ["root_router"]
