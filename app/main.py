from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from bot.create_bot import dp, start_bot, bot, stop_bot
from config import settings
from aiogram.types import Update
from fastapi import FastAPI, Request
from loguru import logger
from api.router import router as api_router
from redis_dao.manager import redis_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Бот запущен...")
    await redis_manager.connect()
    await start_bot()
    app.include_router(api_router)
    webhook_url = settings.hook_url
    await bot.set_webhook(url=webhook_url,
                          allowed_updates=dp.resolve_used_update_types(),
                          drop_pending_updates=True)
    logger.success(f"Вебхук установлен: {webhook_url}")
    yield
    logger.info("Бот остановлен...")
    await stop_bot()
    await redis_manager.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.post("/webhook")
async def webhook(request: Request) -> None:
    logger.info("Получен запрос с вебхука.")
    try:
        update_data = await request.json()
        update = Update.model_validate(update_data, context={"bot": bot})
        await dp.feed_update(bot, update)
        logger.info("Обновление успешно обработано.")
    except Exception as e:
        logger.error(f"Ошибка при обработке обновления с вебхука: {e}")
