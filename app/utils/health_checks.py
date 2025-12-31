import httpx
import time
import logging
from app.core.config import settings
from app.services.blessdatahub_client import BlessdatahubClient
from app.repository.base import BaseRepository

logger = logging.getLogger(__name__)

async def check_service_http(name: str, url: str, method: str = "GET", headers: dict = None, expected_codes: list = [200]):
    """Generic HTTP check."""
    service_start = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers)
            
            latency = (time.time() - service_start) * 1000
            status = "operational" if response.status_code in expected_codes else "degraded"
            return {
                "name": name,
                "status": status,
                "latency": round(latency),
            }
    except Exception as e:
        logger.warning(f"Health check failed for {name}: {e}")
        return {
            "name": name,
            "status": "down",
            "latency": 0,
        }

async def check_database():
    """Check database connection."""
    db_start = time.time()
    try:
        repo = BaseRepository("base_users")
        await repo.get_all(limit=1)
        latency = (time.time() - db_start) * 1000
        return {
            "name": "Supabase Database",
            "status": "operational",
            "latency": round(latency)
        }
    except Exception as e:
        logger.error(f"Health check DB failure: {e}")
        return {
            "name": "Supabase Database",
            "status": "down",
            "latency": 0
        }

async def check_paystack():
    return await check_service_http(
        "Paystack API", 
        f"{settings.PAYSTACK_BASE_URL}", 
        expected_codes=[200, 404]
    )

async def check_blessdatahub():
    # Ping the main site as proxy
    return await check_service_http(
        "Blessdatahub API",
        "https://www.blessdatahub.com", 
        expected_codes=[200, 301, 302]
    )

async def check_telegram():
    return await check_service_http(
        "Telegram Bot",
        f"{settings.TELEGRAM_API_URL}{settings.TELEGRAM_BOT_TOKEN}/getMe"
    )

async def check_whatsapp():
    return await check_service_http(
        "WhatsApp Cloud API",
        f"{settings.WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}",
        headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    )

async def check_all_services():
    import asyncio
    results = await asyncio.gather(
        check_database(),
        check_paystack(),
        check_blessdatahub(),
        check_telegram(),
        check_whatsapp()
    )
    return results
