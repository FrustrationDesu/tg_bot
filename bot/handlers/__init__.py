from aiogram import Router

from .commands import router as commands_router
from .rewards import router as rewards_router
from .ui import router as ui_router

router = Router()
router.include_router(commands_router)
router.include_router(rewards_router)
router.include_router(ui_router)

__all__ = ["router"]
