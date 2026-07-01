from aiogram import Router

from app.handlers import admin, checks, complaints, menu, payments, start, subscription_check, tasks


def setup_routers() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(subscription_check.router)
    router.include_router(menu.router)
    router.include_router(payments.router)
    router.include_router(tasks.router)
    router.include_router(checks.router)
    router.include_router(complaints.router)
    router.include_router(admin.router)
    return router
