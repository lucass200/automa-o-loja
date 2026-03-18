"""
SQLite — persistência de lojas e posts.
Banco salvo em /data/repasse.db no Render (ou ./repasse.db local).
"""

import json
import os
import sqlite3
import time

# No Render, usar /data para persistência entre deploys (Render Disk)
# Localmente usa a pasta do projeto
if os.environ.get("RENDER"):
    DB_DIR = "/data"
    os.makedirs(DB_DIR, exist_ok=True)
else:
    DB_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(DB_DIR, "repasse.db")

LOJAS_DEFAULT = ["repassesgr", "cwb.repasse_", "autopar.repasses"]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria as tabelas se não existirem."""
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

    # Insere lojas padrão se banco estiver vazio
    lojas = ler_lojas()
    if not lojas:
        salvar_lojas(LOJAS_DEFAULT)


# ── Lojas ─────────────────────────────────────────────────────

def ler_lojas():
    with get_conn() as conn:
        rows = conn.execute("SELECT perfil FROM lojas ORDER BY perfil").fetchall()
    return [r["perfil"] for r in rows]


def salvar_lojas(lista):
    """Substitui todas as lojas pela nova lista."""
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


# ── Posts ──────────────────────────────────────────────────────

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
    """Insere post. Retorna False se já existia (duplicata)."""
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
        return False  # duplicata


def salvar_todos_posts(lista: list):
    """Substitui todos os posts (usado pelo scraper)."""
    with get_conn() as conn:
        conn.execute("DELETE FROM posts")
        for post in lista:
            keywords = json.dumps(post.get("keywords", []), ensure_ascii=False)
            conn.execute("""
                INSERT OR REPLACE INTO posts (id, tipo, store, title, description, price, image, url, date, likes, keywords)
                VALUES (:id, :tipo, :store, :title, :description, :price, :image, :url, :date, :likes, :keywords)
            """, {**post, "keywords": keywords})
        conn.commit()
