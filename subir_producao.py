"""
Sobe dados locais (dados.json + lojas.json) para o Render em produção.
Uso: python subir_producao.py
"""

import base64
import json
import os
import urllib.request

RENDER_API = "https://automa-o-loja.onrender.com"


def imagem_para_b64(caminho):
    """Lê imagem do caminho absoluto e retorna base64. Retorna '' se não encontrar."""
    if os.path.exists(caminho):
        with open(caminho, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def baixar_url_para_b64(url):
    """Baixa imagem de URL do Instagram e retorna base64. Retorna '' se falhar."""
    if not url or not url.startswith("http"):
        return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return base64.b64encode(r.read()).decode()
    except Exception:
        return ""

def enviar_lojas():
    print("📋 Enviando lojas...")
    with open("lojas.json", encoding="utf-8") as f:
        lojas = json.load(f)

    for loja in lojas:
        try:
            data = json.dumps({"perfil": loja}, ensure_ascii=False).encode()
            req = urllib.request.Request(
                f"{RENDER_API}/api/lojas/add",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10).close()
        except Exception as e:
            print(f"   ⚠️ {loja}: {e}")

    print(f"   ✅ {len(lojas)} lojas enviadas.")

def mapear_imagens_locais():
    """Monta dict {shortcode: caminho_absoluto} a partir da pasta imagens/."""
    pasta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imagens")
    mapa = {}
    if not os.path.exists(pasta):
        return mapa
    for nome in os.listdir(pasta):
        if not nome.lower().endswith(".jpg"):
            continue
        # nome formato: loja_shortcode.jpg — shortcode é tudo após o último '_'
        partes = nome[:-4].split("_")
        shortcode = partes[-1]
        mapa[shortcode] = os.path.join(pasta, nome)
    return mapa

def enviar_posts():
    print("📤 Enviando posts via sync (substitui tudo com imagens)...")
    with open("dados.json", encoding="utf-8") as f:
        posts = json.load(f)

    mapa = mapear_imagens_locais()
    print(f"   🗂️ {len(mapa)} imagens locais encontradas.")

    payload = []
    sem_imagem = 0
    com_imagem = 0

    for i, post in enumerate(posts):
        p = dict(post)
        shortcode = p.get("id", "")
        caminho = mapa.get(shortcode, "")
        if caminho:
            b64 = imagem_para_b64(caminho)
        else:
            # Tenta baixar da URL do Instagram (enquanto ainda válida)
            b64 = baixar_url_para_b64(p.get("image", ""))

        if b64:
            p["image_b64"] = b64
            com_imagem += 1
        else:
            sem_imagem += 1
        payload.append(p)

        if (i + 1) % 50 == 0:
            print(f"   [{i+1}/{len(posts)}] preparados... 🖼️ {com_imagem} com imagem | ⚠️ {sem_imagem} sem")

    print(f"\n   Total: {len(payload)} posts | 🖼️ {com_imagem} com imagem | ⚠️ {sem_imagem} sem imagem local")

    # Envia em lotes de 30 para não estourar o limite do Render
    LOTE = 30
    # Primeiro lote usa sync (limpa tudo), os demais usam add por post
    print(f"   Enviando lote 1 via /api/posts/sync (limpa banco) ...")
    primeiro_lote = payload[:LOTE]
    data = json.dumps(primeiro_lote, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{RENDER_API}/api/posts/sync",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read().decode())
            print(f"   ✅ {resp.get('msg', 'ok')}")
    except Exception as e:
        print(f"   ⚠️ Erro no lote 1: {e}")
        return

    # Lotes restantes via /api/posts/add
    restantes = payload[LOTE:]
    enviados = len(primeiro_lote)
    erros = 0
    for i, post in enumerate(restantes):
        try:
            data = json.dumps(post, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                f"{RENDER_API}/api/posts/add",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=30).close()
            enviados += 1
        except Exception:
            erros += 1

        idx = LOTE + i + 1
        if idx % 50 == 0:
            print(f"   [{idx}/{len(payload)}] ✅ {enviados} enviados | ⚠️ {erros} erros")

    print(f"\n🎉 Concluído! ✅ {enviados} posts | ⚠️ {erros} erros")

if __name__ == "__main__":
    print(f"🚀 Subindo dados para {RENDER_API}\n")
    enviar_lojas()
    print()
    enviar_posts()
