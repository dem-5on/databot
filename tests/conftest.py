import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect(
        user="postgres",
        password="WKR3dsFNsmfQhQbe",
        database="postgres",
        host="aws-1-eu-west-1.pooler.supabase.com",
        port=5432,
        ssl="require"
    )
    print("Connected!")
    await conn.close()

asyncio.run(test())
