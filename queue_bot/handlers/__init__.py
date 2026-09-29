from aiogram import Router

from queue_bot.handlers import admin, chat_events, client, errors, fallback


def build_router() -> Router:
    router = Router(name="root")
    router.include_routers(
        errors.build_router(),
        chat_events.build_router(),
        client.build_router(),
        admin.build_router(),
        fallback.build_router(),
    )
    return router
