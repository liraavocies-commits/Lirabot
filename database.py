import aiosqlite
from pathlib import Path


class Database:
    def __init__(self, path):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys=ON")
            await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS anime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                genre TEXT DEFAULT '',
                description TEXT DEFAULT '',
                cover_url TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anime_id INTEGER NOT NULL
                    REFERENCES anime(id) ON DELETE CASCADE,
                number INTEGER NOT NULL,
                title TEXT DEFAULT '',
                video_file_id TEXT NOT NULL,
                UNIQUE(anime_id, number)
            );

            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL UNIQUE,
                title TEXT DEFAULT '',
                invite_url TEXT DEFAULT ''
            );
            """)
            await db.commit()

    async def add_user(self, user_id, username="", full_name=""):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                INSERT INTO users(user_id, username, full_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    full_name=excluded.full_name
            """, (user_id, username, full_name))
            await db.commit()

    async def add_anime(self, title, genre, description, cover_url):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("""
                INSERT INTO anime(title, genre, description, cover_url)
                VALUES (?, ?, ?, ?)
            """, (title, genre, description, cover_url))
            await db.commit()
            return cur.lastrowid

    async def list_anime(self):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("""
                SELECT id, title, genre, description, cover_url
                FROM anime ORDER BY title COLLATE NOCASE
            """)
            rows = await cur.fetchall()
            return [
                dict(id=r[0], title=r[1], genre=r[2],
                     description=r[3], cover_url=r[4])
                for r in rows
            ]

    async def get_anime(self, anime_id):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("""
                SELECT id, title, genre, description, cover_url
                FROM anime WHERE id=?
            """, (anime_id,))
            r = await cur.fetchone()
            if not r:
                return None
            return dict(
                id=r[0], title=r[1], genre=r[2],
                description=r[3], cover_url=r[4]
            )

    async def search_anime(self, query):
        async with aiosqlite.connect(self.path) as db:
            pattern = f"%{query.lower()}%"
            cur = await db.execute("""
                SELECT id, title, genre, description, cover_url
                FROM anime
                WHERE lower(title) LIKE ?
                   OR lower(genre) LIKE ?
                ORDER BY title LIMIT 30
            """, (pattern, pattern))
            rows = await cur.fetchall()
            return [
                dict(id=r[0], title=r[1], genre=r[2],
                     description=r[3], cover_url=r[4])
                for r in rows
            ]

    async def add_episode(
        self, anime_id, number, title, video_file_id
    ):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                INSERT INTO episodes(
                    anime_id, number, title, video_file_id
                ) VALUES (?, ?, ?, ?)
            """, (anime_id, number, title, video_file_id))
            await db.commit()

    async def get_episodes(self, anime_id):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("""
                SELECT id, anime_id, number, title, video_file_id
                FROM episodes WHERE anime_id=?
                ORDER BY number
            """, (anime_id,))
            rows = await cur.fetchall()
            return [
                dict(id=r[0], anime_id=r[1], number=r[2],
                     title=r[3], video_file_id=r[4])
                for r in rows
            ]

    async def get_episode(self, episode_id):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("""
                SELECT id, anime_id, number, title, video_file_id
                FROM episodes WHERE id=?
            """, (episode_id,))
            r = await cur.fetchone()
            if not r:
                return None
            return dict(
                id=r[0], anime_id=r[1], number=r[2],
                title=r[3], video_file_id=r[4]
            )

    async def get_genres(self):
        anime = await self.list_anime()
        genres = set()
        for item in anime:
            for genre in item["genre"].split(","):
                if genre.strip():
                    genres.add(genre.strip())
        return sorted(genres, key=str.lower)

    async def list_by_genre(self, genre):
        items = await self.list_anime()
        return [
            a for a in items
            if genre.lower() in [
                g.strip().lower() for g in a["genre"].split(",")
            ]
        ]

    async def update_anime(self, anime_id, field, value):
        allowed = {"title", "genre", "description", "cover_url"}
        if field not in allowed:
            raise ValueError("Noto‘g‘ri maydon")
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"UPDATE anime SET {field}=? WHERE id=?",
                (value, anime_id)
            )
            await db.commit()

    async def delete_anime(self, anime_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys=ON")
            await db.execute(
                "DELETE FROM anime WHERE id=?", (anime_id,)
            )
            await db.commit()

    async def add_channel(self, chat_id, title, invite_url):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                INSERT INTO channels(chat_id, title, invite_url)
                VALUES (?, ?, ?)
            """, (chat_id, title, invite_url))
            await db.commit()

    async def get_channels(self):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("""
                SELECT id, chat_id, title, invite_url
                FROM channels ORDER BY id
            """)
            rows = await cur.fetchall()
            return [
                dict(id=r[0], chat_id=r[1],
                     title=r[2], invite_url=r[3])
                for r in rows
            ]

    async def remove_channel(self, channel_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "DELETE FROM channels WHERE id=?", (channel_id,)
            )
            await db.commit()

    async def get_users(self):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT user_id FROM users")
            return [r[0] for r in await cur.fetchall()]

    async def stats(self):
        async with aiosqlite.connect(self.path) as db:
            result = {}
            for table in ("users", "anime", "episodes", "channels"):
                cur = await db.execute(
                    f"SELECT COUNT(*) FROM {table}"
                )
                result[table] = (await cur.fetchone())[0]
            return result
