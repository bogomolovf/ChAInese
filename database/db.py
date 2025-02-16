import logging
import psycopg2
import asyncio
import asyncpg




DATABASE_URL = "postgresql://postgres.uilrtenermvclsnjlcym:goodgame2254FF@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

logger = logging.getLogger(__name__)




async def connect_db():
    return await asyncpg.connect(DATABASE_URL)

async def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                nickname TEXT NOT NULL,
                email TEXT UNIQUE
            );

            CREATE TABLE IF NOT EXISTS flashcards (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                pinyin TEXT NOT NULL,
                context TEXT,
                list_id INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lists (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                list_name TEXT NOT NULL UNIQUE
            ); 

            """)
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")


def sync_db_execute(query, params=()):
    """
    Выполняет SQL-запрос в синхронном режиме (для `asyncio.to_thread`).
    """
    conn = asyncio.run(connect_db())  # Исправлено: ждем выполнения `connect_db()`
    cur = conn.cursor()
    cur.execute(query, params)
    result = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return result


# Асинхронный запрос в БД
async def db_execute(query, params=()):
    """
    Выполняет SQL-запрос в асинхронном режиме.
    """
    conn = await connect_db()  # Исправлено: добавлен `await`
    try:
        async with conn.transaction():
            result = await conn.fetch(query, *params)
        return result
    finally:
        await conn.close()