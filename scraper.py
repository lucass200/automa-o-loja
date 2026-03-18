"""
=======================================================
  REPASSE CENTRAL — Scraper RÁPIDO
  Coleta da grade sem abrir cada post individualmente
  ~3 min para 3 perfis (vs 20+ min do modo lento)
=======================================================

COMO USAR:
  1. pip install --user playwright
  2. python -m playwright install chromium
  3. python scraper.py
     -> Chrome abre, faça login (pelo Facebook)
     -> Coleta tudo e fecha

Próximas vezes: login já está salvo. Só python scraper.py
"""

import json, os, re, time
from playwright.sync_api import sync_playwright

PERFIS = [
    "repassesgr",
    "cwb.repasse_",
    "autopar.repasses",
]

MAX_POSTS     = 30
OUTPUT_JS     = "dados.js"
OUTPUT_JSON   = "dados.json"
PASTA_IMAGENS = "imagens"
PASTA_SESSAO  = "sessao_ig"

def extrair_preco(txt):
    m = re.search(r'R\$\s?[\d.,]+', txt or "", re.I)
    return m.group(0) if m else "Consulte"

def extrair_titulo(txt):
    if not txt: return "Veículo disponível"
    l = txt.strip().split('\n')[0].replace('*','').replace('#','').strip()
    return (l[:65]+"…") if len(l)>65 else (l or "Veículo disponível")

def fechar_popup(page):
    for t in ["Agora não","Not Now","Aceitar todos","Allow all cookies","Fechar"]:
        try: page.get_by_role("button", name=t).click(timeout=1500)
        except: pass

def garantir_login(page):
    print("🔐 Verificando login...")
    page.goto("https://www.instagram.com/", timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    fechar_popup(page)
    logado = (page.locator('[aria-label="Home"],[aria-label="Página inicial"]').count() > 0
              or page.locator('a[href="/"]').count() > 0)
    if not logado:
        print("\n📱 Faça login no Instagram na janela aberta (pode ser pelo Facebook).")
        print("   O script continua automaticamente após o login.\n")
        page.wait_for_selector('[aria-label="Home"],[aria-label="Página inicial"]', timeout=180000)
        page.wait_for_timeout(1500)
        fechar_popup(page)
        print("   ✅ Login OK! Sessão salva.\n")
    else:
        print("   ✅ Sessão ativa, sem precisar logar.\n")

def coletar_perfil_rapido(page, perfil):
    """
    Modo RÁPIDO: coleta informações direto da grade do perfil.
    Abre o lightbox (popup) de cada post para pegar legenda — muito mais
    rápido do que navegar para cada URL individual.
    """
    print(f"📥 @{perfil} — coletando grade...")
    posts = []

    page.goto(f"https://www.instagram.com/{perfil}/", timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    fechar_popup(page)

    # Scroll para carregar mais posts
    links_vistos = set()
    for _ in range(8):
        for a in page.locator('a[href*="/p/"]').all():
            href = (a.get_attribute("href") or "").split("?")[0]
            if "/p/" in href:
                links_vistos.add(href)
        if len(links_vistos) >= MAX_POSTS: break
        page.evaluate("window.scrollBy(0,1800)")
        page.wait_for_timeout(1200)

    links = list(links_vistos)[:MAX_POSTS]
    print(f"   {len(links)} posts encontrados. Coletando detalhes...")
    os.makedirs(PASTA_IMAGENS, exist_ok=True)

    for i, href in enumerate(links):
        try:
            # Clica no post para abrir o lightbox (muito mais rápido que navegar)
            a_el = page.locator(f'a[href="{href}"], a[href="{href}?"]').first
            
            # Força o elemento a ficar visível antes de clicar
            try:
                a_el.evaluate("el => el.scrollIntoViewIfNeeded()")
                page.wait_for_timeout(300)
            except:
                pass

            # Aumenta timeout para 8s e força o clique se estiver sobreposto
            a_el.click(timeout=8000, force=True)
            page.wait_for_timeout(1500)

            shortcode = href.strip("/").split("/")[-1]
            link_post = f"https://www.instagram.com/p/{shortcode}/"

            # Legenda no lightbox
            legenda = ""
            for sel in ['[role="dialog"] h1', '[role="dialog"] span > div > span',
                        'article h1', 'h1', '[role="presentation"] h1']:
                try:
                    legenda = page.locator(sel).first.inner_text(timeout=2500).strip()
                    if legenda: break
                except: pass

            # Se não achou legenda de jeito nenhum, tenta pegar a primeira div de texto longo dentro do dialog
            if not legenda:
                try:
                    textos = page.locator('[role="dialog"] span').all_inner_texts()
                    longos = [t for t in textos if len(t) > 30]
                    if longos: legenda = longos[0]
                except: pass

            # Imagem no lightbox
            img_src = ""
            try:
                img_src = page.locator('[role="dialog"] img, article img').first.get_attribute("src", timeout=2500) or ""
            except: pass

            nome_img = f"{PASTA_IMAGENS}/{perfil}_{shortcode}.jpg"
            if img_src:
                try:
                    r = page.request.get(img_src)
                    with open(nome_img, "wb") as f: f.write(r.body())
                except: nome_img = ""

            palavras = [w.strip('#@').lower() for w in legenda.split() if len(w)>3]
            posts.append({
                "id":          shortcode,
                "tipo":        "post",
                "store":       f"@{perfil}",
                "title":       extrair_titulo(legenda),
                "description": legenda[:400] or "Sem descrição.",
                "price":       extrair_preco(legenda),
                "image":       nome_img if os.path.exists(nome_img) else "",
                "url":         link_post,
                "date":        time.strftime("%d/%m/%Y"),
                "likes":       0,
                "keywords":    palavras[:25],
            })
            print(f"   [{i+1}/{len(links)}] {extrair_titulo(legenda)[:50]}")

            # Fecha o lightbox pressionando Escape (ou clicando no X via coords se falhar)
            try:
                page.keyboard.press("Escape")
            except:
                pass
            page.wait_for_timeout(600)

        except Exception as e:
            msg_erro = str(e).split('\n')[0][:60]
            print(f"   ⚠️  [{i+1}/{len(links)}] Erro ao abrir: {msg_erro}")
            try: page.keyboard.press("Escape")
            except: pass
            page.wait_for_timeout(500)

    print(f"   ✅ {len(posts)} posts coletados de @{perfil}\n")
    return posts

def coletar_stories_rapido(page, perfil):
    """Coleta stories ativos (duram 24h)."""
    print(f"   📸 Stories de @{perfil}...")
    stories = []
    try:
        page.goto(f"https://www.instagram.com/stories/{perfil}/", timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        if "stories" not in page.url:
            print(f"   ℹ️  Sem stories ativos.")
            return []

        for slide in range(15):
            page.wait_for_timeout(1000)
            img_src = ""
            try: img_src = page.locator('section img[src*="cdninstagram"],section img[src*="fbcdn"]').first.get_attribute("src", timeout=2000) or ""
            except: pass
            if not img_src: break

            ts = int(time.time())
            nome = f"{PASTA_IMAGENS}/story_{perfil}_{slide}_{ts}.jpg"
            try:
                r = page.request.get(img_src)
                with open(nome, "wb") as f: f.write(r.body())
            except: nome = ""

            stories.append({
                "id": f"story_{perfil}_{ts}", "tipo": "story",
                "store": f"@{perfil}", "title": f"Story de @{perfil}",
                "description": f"Story capturado em {time.strftime('%d/%m/%Y %H:%M')} — dura 24h.",
                "price": "Consulte", "image": nome if os.path.exists(nome) else "",
                "url": f"https://www.instagram.com/{perfil}/",
                "date": time.strftime("%d/%m/%Y"), "likes": 0,
                "keywords": ["story", perfil.lower()],
            })
            print(f"     Story {slide+1} ✓")

            # Avança slide
            try: page.mouse.click(page.viewport_size['width']*0.75, page.viewport_size['height']*0.5)
            except: break
            if perfil not in page.url: break

    except Exception as e:
        print(f"   ⚠️  Erro: {e}")

    print(f"   ✅ {len(stories)} stories de @{perfil}")
    return stories

def salvar(dados):
    # dados.js (para abrir direto no browser)
    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write(f"// Atualizado: {time.strftime('%d/%m/%Y %H:%M')}\n")
        f.write("const CAR_DATA = ")
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    # dados.json (para a API Flask)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_lojas():
    try:
        import db
        db.init_db()
        lojas = db.ler_lojas()
        if lojas:
            return lojas
    except Exception as e:
        print(f"⚠️ Banco indisponível, usando lojas.json: {e}")
    # Fallback para lojas.json
    try:
        if os.path.exists("lojas.json"):
            with open("lojas.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return ["repassesgr", "cwb.repasse_", "autopar.repasses"]

def coletar_dados():
    os.makedirs(PASTA_SESSAO, exist_ok=True)
    os.makedirs(PASTA_IMAGENS, exist_ok=True)
    todos = []

    # Carrega lojas cadastradas no dashboard
    perfis_dinamicos = carregar_lojas()
    if not perfis_dinamicos:
        print("📥 Nenhuma loja cadastrada! Adicione perfis no dashboard primeiro.")
        salvar([])
        return

    # Se estiver rodando no Docker/Render/Railway (ambiente s/ tela), o headless deve ser True. 
    # Em casa (para logar), rodar com =False
    is_cloud = os.environ.get("RENDER") is not None or os.environ.get("RAILWAY_ENVIRONMENT") is not None
    use_headless = True if is_cloud else False

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=PASTA_SESSAO,
            headless=use_headless,
            args=["--start-maximized", "--no-sandbox", "--disable-setuid-sandbox"],
            no_viewport=True,
        )
        page = ctx.new_page()
        garantir_login(page)

        for perfil in perfis_dinamicos:
            print(f"\n{'='*45}\n📦 @{perfil}\n{'='*45}")
            todos += coletar_perfil_rapido(page, perfil)
            todos += coletar_stories_rapido(page, perfil)

        ctx.close()

    salvar(todos)
    p = sum(1 for x in todos if x["tipo"]=="post")
    s = sum(1 for x in todos if x["tipo"]=="story")
    print(f"\n🎉 Concluído! {p} posts + {s} stories → dados.json")
    print("▶️  Inicie a API:  python api.py\n")

if __name__ == "__main__":
    coletar_dados()
