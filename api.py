"""
=======================================================
  REPASSE CENTRAL — API Flask
  Serve o dashboard + dados via HTTP
=======================================================

COMO USAR:
  1. pip install --user flask flask-cors
  2. python api.py
  3. Acesse: http://localhost:5000
  4. Para clientes: use ngrok ou Railway para expor

O scraper roda automaticamente todo dia às 8h.
"""

import json
import os
import threading
import time
import schedule
from datetime import datetime
from flask import Flask, jsonify, send_from_directory, send_file
from flask_cors import CORS

# ── Config ────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DADOS_FILE  = os.path.join(BASE_DIR, "dados.js")
DADOS_JSON  = os.path.join(BASE_DIR, "dados.json")  # versão JSON pura para a API

app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)  # permite acesso de qualquer origem (frontend externo)

# ── Estado do scraper ─────────────────────────────────────────
scraper_status = {
    "rodando":      False,
    "ultima_coleta": None,
    "total_posts":   0,
    "total_stories": 0,
    "erro":          None,
}

# ── Endpoints ─────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve o dashboard."""
    return send_file(os.path.join(BASE_DIR, "index.html"))

@app.route("/<path:filename>")
def static_files(filename):
    """Serve arquivos estáticos (CSS, JS, imagens)."""
    return send_from_directory(BASE_DIR, filename)

@app.route("/api/dados")
def get_dados():
    """Retorna todos os posts e stories em JSON."""
    if not os.path.exists(DADOS_JSON):
        return jsonify([])
    try:
        with open(DADOS_JSON, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return jsonify(dados)
    except Exception as e:
        print(f"⚠️ Aviso: Falha ao ler dados.json na rota /api/dados: {e}")
        return jsonify([])

@app.route("/api/status")
def get_status():
    """Retorna o status do scraper (última coleta, total de posts etc.)."""
    return jsonify(scraper_status)

# ── Gerenciamento de Lojas ────────────────────────────────────

LOJAS_FILE = os.path.join(BASE_DIR, "lojas.json")

def ler_lojas():
    if not os.path.exists(LOJAS_FILE):
        return ["repassesgr", "cwb.repasse_", "autopar.repasses"]
    with open(LOJAS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_lojas(lista):
    with open(LOJAS_FILE, "w", encoding="utf-8") as f:
        json.dump(lista, f, indent=2)

@app.route("/api/lojas", methods=["GET"])
def listar_lojas():
    return jsonify(ler_lojas())

@app.route("/api/lojas/add", methods=["POST"])
def adicionar_loja():
    from flask import request
    data = request.json or {}
    novo_perfil = data.get("perfil", "").strip().replace("@", "").lower()
    
    if not novo_perfil:
        return jsonify({"erro": "Perfil inválido"}), 400
        
    lojas = ler_lojas()
    if novo_perfil in lojas:
        return jsonify({"erro": "Loja já cadastrada"}), 400
        
    lojas.append(novo_perfil)
    salvar_lojas(lojas)
    return jsonify({"msg": f"@{novo_perfil} adicionado!", "lojas": lojas})

@app.route("/api/lojas/remove", methods=["POST"])
def remover_loja():
    from flask import request
    data = request.json or {}
    perfil = data.get("perfil", "").strip().replace("@", "").lower()
    
    lojas = ler_lojas()
    if perfil in lojas:
        lojas.remove(perfil)
        salvar_lojas(lojas)
        return jsonify({"msg": f"@{perfil} removido!", "lojas": lojas})
    
    return jsonify({"erro": "Loja não encontrada"}), 404

# ── Ações Scraper ─────────────────────────────────────────────

@app.route("/api/atualizar", methods=["POST"])
def atualizar():
    """Dispara uma nova rodada do scraper manualmente."""
    if scraper_status["rodando"]:
        return jsonify({"msg": "Scraper já está rodando. Aguarde."}), 429

    thread = threading.Thread(target=rodar_scraper, daemon=True)
    thread.start()
    return jsonify({"msg": "Coleta iniciada! Acompanhe em /api/status"})

# ── Scraper ───────────────────────────────────────────────────

def rodar_scraper():
    """Roda o Playwright scraper e salva os dados em JSON."""
    scraper_status["rodando"] = True
    scraper_status["erro"]    = None
    print(f"\n🔄 [{datetime.now().strftime('%H:%M')}] Iniciando coleta...")

    try:
        # Importa e executa a lógica do scraper
        import importlib.util
        spec   = importlib.util.spec_from_file_location("scraper", os.path.join(BASE_DIR, "scraper.py"))
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        modulo.coletar_dados()

        # Converte dados.js → dados.json para a API consumir
        converter_para_json()

        # Atualiza status
        with open(DADOS_JSON, "r", encoding="utf-8") as f:
            dados = json.load(f)

        scraper_status["ultima_coleta"]  = datetime.now().strftime("%d/%m/%Y %H:%M")
        scraper_status["total_posts"]    = sum(1 for d in dados if d.get("tipo") == "post")
        scraper_status["total_stories"]  = sum(1 for d in dados if d.get("tipo") == "story")
        print(f"✅ Coleta concluída: {scraper_status['total_posts']} posts + {scraper_status['total_stories']} stories")

    except Exception as e:
        scraper_status["erro"] = str(e)
        print(f"❌ Erro na coleta: {e}")

    finally:
        scraper_status["rodando"] = False

def converter_para_json():
    """Lê dados.js e extrai o JSON puro para dados.json."""
    if not os.path.exists(DADOS_FILE):
        return
    with open(DADOS_FILE, "r", encoding="utf-8") as f:
        conteudo = f.read()
    # Remove as 2 linhas de comentário e extrai só o JSON
    linhas = conteudo.strip().split('\n')
    json_str = '\n'.join(l for l in linhas if not l.startswith('//') and not l.startswith('const CAR_DATA'))
    # Remove o ; final se existir
    json_str = json_str.strip().rstrip(';')
    with open(DADOS_JSON, "w", encoding="utf-8") as f:
        f.write(json_str)

# ── Agendamento (roda todo dia às 8h) ─────────────────────────

def agendar_coleta():
    schedule.every().day.at("08:00").do(rodar_scraper)
    while True:
        schedule.run_pending()
        time.sleep(60)

# ── Main ──────────────────────────────────────────────────────

if __name__ == "__main__":
    # Carrega dados existentes ao iniciar
    if os.path.exists(DADOS_FILE) and not os.path.exists(DADOS_JSON):
        converter_para_json()

    if os.path.exists(DADOS_JSON):
        try:
            with open(DADOS_JSON, "r", encoding="utf-8") as f:
                dados = json.load(f)
            scraper_status["total_posts"]   = sum(1 for d in dados if d.get("tipo") == "post")
            scraper_status["total_stories"] = sum(1 for d in dados if d.get("tipo") == "story")
        except json.JSONDecodeError:
            print("⚠️ Aviso: dados.json está vazio ou inválido. O dashboard usará os dados de exemplo até a próxima coleta.")


    # Thread do agendador (coleta diária)
    t = threading.Thread(target=agendar_coleta, daemon=True)
    t.start()

    print("\n" + "="*50)
    print("  🚗 REPASSE CENTRAL — API Rodando!")
    print("="*50)
    print(f"  🌐 Dashboard: http://localhost:5000")
    print(f"  📡 API dados: http://localhost:5000/api/dados")
    print(f"  🔄 Atualizar: POST http://localhost:5000/api/atualizar")
    print(f"  ⏰ Coleta automática: todo dia às 08:00")
    print("="*50 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=False)
