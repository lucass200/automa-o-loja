"""
Persistência — PostgreSQL (Supabase) em produção, SQLite local.
"""

import json
import os
import sqlite3

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Testa conexão PG antes de decidir qual backend usar
USE_PG = False
if DATABASE_URL:
    try:
        import psycopg2 as _test_pg
        _conn = _test_pg.connect(DATABASE_URL, connect_timeout=5)
        _conn.close()
        USE_PG = True
        print("✅ Conectado ao Supabase (PostgreSQL)")
    except Exception as _e:
        print(f"⚠️ Supabase indisponível, usando SQLite: {_e}")
        USE_PG = False

LOJAS_DEFAULT = ["repassesgr", "cwb.repasse_", "autopar.repasses"]

# ── PostgreSQL ─────────────────────────────────────────────────
if USE_PG:
    import psycopg2
    import psycopg2.extras

    def get_conn():
        return psycopg2.connect(DATABASE_URL, connect_timeout=5)

    def init_db():
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS lojas (
                        perfil TEXT PRIMARY KEY
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS posts (
                        id          TEXT PRIMARY KEY,
                        tipo        TEXT DEFAULT 'post',
                        store       TEXT,
                        title       TEXT,
                        description TEXT,
                        price       TEXT DEFAULT 'Consulte',
                        image       TEXT,
                        url         TEXT,
                        date        TEXT,
                        likes       INTEGER DEFAULT 0,
                        keywords    TEXT,
                        created_at  BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT
                    )
                """)
            conn.commit()
        lojas = ler_lojas()
        if not lojas:
            salvar_lojas(LOJAS_DEFAULT)

    def ler_lojas():
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT perfil FROM lojas ORDER BY perfil")
                return [r["perfil"] for r in cur.fetchall()]

    def salvar_lojas(lista):
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM lojas")
                for p in lista:
                    cur.execute("INSERT INTO lojas (perfil) VALUES (%s) ON CONFLICT DO NOTHING", (p,))
            conn.commit()

    def adicionar_loja(perfil):
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO lojas (perfil) VALUES (%s) ON CONFLICT DO NOTHING", (perfil,))
            conn.commit()

    def remover_loja(perfil):
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM lojas WHERE perfil = %s", (perfil,))
            conn.commit()

    def ler_posts():
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM posts ORDER BY created_at DESC")
                rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["keywords"] = json.loads(d["keywords"] or "[]")
            del d["created_at"]
            result.append(d)
        return result

    def adicionar_post(post: dict) -> bool:
        keywords = json.dumps(post.get("keywords", []), ensure_ascii=False)
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO posts (id, tipo, store, title, description, price, image, url, date, likes, keywords)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        post.get("id"), post.get("tipo", "post"), post.get("store"),
                        post.get("title"), post.get("description"), post.get("price", "Consulte"),
                        post.get("image"), post.get("url"), post.get("date"),
                        post.get("likes", 0), keywords
                    ))
                conn.commit()
            return True
        except psycopg2.IntegrityError:
            return False

    def salvar_todos_posts(lista: list):
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM posts")
                for post in lista:
                    keywords = json.dumps(post.get("keywords", []), ensure_ascii=False)
                    cur.execute("""
                        INSERT INTO posts (id, tipo, store, title, description, price, image, url, date, likes, keywords)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (
                        post.get("id"), post.get("tipo", "post"), post.get("store"),
                        post.get("title"), post.get("description"), post.get("price", "Consulte"),
                        post.get("image"), post.get("url"), post.get("date"),
                        post.get("likes", 0), keywords
                    ))
            conn.commit()

# ── SQLite (local) ─────────────────────────────────────────────
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repasse.db")

    def get_conn():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db():
        with get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lojas (
                    perfil TEXT PRIMARY KEY
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id          TEXT PRIMARY KEY,
                    tipo        TEXT DEFAULT 'post',
                    store       TEXT,
                    title       TEXT,
                    description TEXT,
                    price       TEXT DEFAULT 'Consulte',
                    image       TEXT,
                    url         TEXT,
                    date        TEXT,
                    likes       INTEGER DEFAULT 0,
                    keywords    TEXT,
                    created_at  INTEGER DEFAULT (strftime('%s','now'))
                )
            """)
            conn.commit()
        lojas = ler_lojas()
        if not lojas:
            salvar_lojas(LOJAS_DEFAULT)

    def ler_lojas():
        with get_conn() as conn:
            rows = conn.execute("SELECT perfil FROM lojas ORDER BY perfil").fetchall()
        return [r["perfil"] for r in rows]

    def salvar_lojas(lista):
        with get_conn() as conn:
            conn.execute("DELETE FROM lojas")
            conn.executemany("INSERT OR IGNORE INTO lojas (perfil) VALUES (?)", [(p,) for p in lista])
            conn.commit()

    def adicionar_loja(perfil):
        with get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO lojas (perfil) VALUES (?)", (perfil,))
            conn.commit()

    def remover_loja(perfil):
        with get_conn() as conn:
            conn.execute("DELETE FROM lojas WHERE perfil = ?", (perfil,))
            conn.commit()

    def ler_posts():
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM posts ORDER BY created_at DESC").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["keywords"] = json.loads(d["keywords"] or "[]")
            del d["created_at"]
            result.append(d)
        return result

    def adicionar_post(post: dict) -> bool:
        keywords = json.dumps(post.get("keywords", []), ensure_ascii=False)
        try:
            with get_conn() as conn:
                conn.execute("""
                    INSERT INTO posts (id, tipo, store, title, description, price, image, url, date, likes, keywords)
                    VALUES (:id, :tipo, :store, :title, :description, :price, :image, :url, :date, :likes, :keywords)
                """, {**post, "keywords": keywords})
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def salvar_todos_posts(lista: list):
        with get_conn() as conn:
            conn.execute("DELETE FROM posts")
            for post in lista:
                keywords = json.dumps(post.get("keywords", []), ensure_ascii=False)
                conn.execute("""
                    INSERT OR REPLACE INTO posts (id, tipo, store, title, description, price, image, url, date, likes, keywords)
                    VALUES (:id, :tipo, :store, :title, :description, :price, :image, :url, :date, :likes, :keywords)
                """, {**post, "keywords": keywords})
            conn.commit()
