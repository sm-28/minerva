import asyncio
import os
import asyncpg
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("TestSubscriber")

async def notification_handler(con, pid, channel, payload):
    logger.info(f"🔔 Received NOTIFY on channel '{channel}'!")
    logger.info(f"   Payload (Client ID): {payload}")
    logger.info("   -> Invalidating local memory cache for this client now...")

async def main():
    logger.info("Connecting to PostgreSQL...")
    conn = await asyncpg.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        database=os.environ.get("DB_NAME", "minerva"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "postgres"),
        port=os.environ.get("DB_PORT", "5432")
    )

    logger.info("Connected successfully.")
    
    # Subscribe to the Postgres channel
    await conn.add_listener("index_updates", notification_handler)
    logger.info("✅ Subscribed to 'index_updates'. Waiting for ingestion to finish...")

    try:
        # Keep the connection open indefinitely
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await conn.remove_listener("index_updates", notification_handler)
        await conn.close()
        logger.info("Disconnected.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
