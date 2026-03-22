const express = require("express");
const cors = require("cors");
const mysql = require("mysql2/promise");
const path = require("path");
const fs = require("fs");
const crypto = require("crypto");

const app = express();
app.use(cors());
app.use(express.json({ limit: "50mb" }));

// ── Banco de Dados MySQL (Hostinger) ───────────────────────────
const DB_CONFIG = {
  host: "localhost",
  user: "u221220547_jonatancgi",
  password: "2Art9Cm#TUxYUC6",
  database: "u221220547_jcmotors",
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
};

const IMAGENS_DIR = path.join(__dirname, "imagens");
if (!fs.existsSync(IMAGENS_DIR)) fs.mkdirSync(IMAGENS_DIR);

let pool = null;
try {
  pool = mysql.createPool(DB_CONFIG);
  console.log("✅ Pool MySQL configurado");
} catch (e) {
  console.error("❌ Erro ao criar pool MySQL:", e.message);
}

// ── Init Tabelas ───────────────────────────────────────────────
async function initDb() {
  if (!pool) return;
  try {
    const conn = await pool.getConnection();
    await conn.query(`
      CREATE TABLE IF NOT EXISTS lojas (
        perfil VARCHAR(100) PRIMARY KEY
      )
    `);
    await conn.query(`
      CREATE TABLE IF NOT EXISTS posts (
        id          VARCHAR(100) PRIMARY KEY,
        tipo        VARCHAR(50) DEFAULT 'post',
        store       VARCHAR(100),
        title       VARCHAR(255),
        description TEXT,
        price       VARCHAR(50) DEFAULT 'Consulte',
        image       TEXT,
        url         TEXT,
        date        VARCHAR(20),
        likes       INT DEFAULT 0,
        keywords    TEXT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    
    // Lojas padrão
    const [rows] = await conn.query("SELECT COUNT(*) as c FROM lojas");
    if (rows[0].c === 0) {
      const defaults = ["repassesgr", "cwb.repasse_", "autopar.repasses"];
      for (const p of defaults) {
        await conn.query("INSERT IGNORE INTO lojas (perfil) VALUES (?)", [p]);
      }
    }
    conn.release();
    console.log("✅ MySQL Tabelas verificadas");
  } catch (e) {
    console.error("⚠️ Falha ao iniciar tabelas MySQL:", e.message);
  }
}

// ── Helpers Imagem ─────────────────────────────────────────────
function salvarImagemB64(postId, b64Full) {
  try {
    // Detecta se é Base64 real (data:image/...)
    if (!b64Full || !b64Full.includes("base64,")) return b64Full;

    const parts = b64Full.split("base64,");
    const mime = parts[0].match(/:(.*?);/)[1];
    const extension = mime.split("/")[1] || "jpg";
    const b64Data = parts[1];

    const buf = Buffer.from(b64Data, "base64");
    const fname = crypto.createHash("md5").update(postId).digest("hex") + "." + extension;
    const fullPath = path.join(IMAGENS_DIR, fname);
    
    fs.writeFileSync(fullPath, buf);
    console.log(`💾 Imagem salva: ${fname}`);
    return `/api/imagens/${fname}`; // Retorna o link curto para o banco
  } catch (e) {
    console.error("⚠️ Erro ao salvar imagem:", e.message);
    return b64Full; // Retorna o que veio se falhar
  }
}

// ── Rotas Estáticas ────────────────────────────────────────────
app.use("/api/imagens", express.static(IMAGENS_DIR));
app.use(express.static(__dirname));
app.get("/", (req, res) => res.sendFile(path.join(__dirname, "index.html")));

// ── API Lojas ──────────────────────────────────────────────────
app.get("/api/lojas", async (req, res) => {
  if (!pool) return res.json([]);
  try {
    const [rows] = await pool.query("SELECT perfil FROM lojas ORDER BY perfil");
    res.json(rows.map(r => r.perfil));
  } catch (e) { res.json([]); }
});

app.post("/api/lojas/add", async (req, res) => {
  if (!pool) return res.status(503).json({ erro: "Banco indisponível" });
  const data = req.body || {};
  let perfis = Array.isArray(data.perfis) ? data.perfis : (data.perfil ? [data.perfil] : []);

  if (!perfis.length) return res.status(400).json({ erro: "Nenhum perfil" });

  try {
    for (const p of perfis) {
      const limpo = p.trim().replace("@", "").split("/").pop().toLowerCase();
      if (limpo) await pool.query("INSERT IGNORE INTO lojas (perfil) VALUES (?)", [limpo]);
    }
    const [rows] = await pool.query("SELECT perfil FROM lojas ORDER BY perfil");
    res.json({ msg: "OK", lojas: rows.map(r => r.perfil) });
  } catch (e) { res.status(500).json({ erro: e.message }); }
});

app.post("/api/lojas/remove", async (req, res) => {
  if (!pool) return res.status(503).json({ erro: "Banco indisponível" });
  try {
    const perfil = (req.body.perfil || "").trim().replace("@", "").toLowerCase();
    await pool.query("DELETE FROM lojas WHERE perfil = ?", [perfil]);
    const [rows] = await pool.query("SELECT perfil FROM lojas ORDER BY perfil");
    res.json({ msg: "Removido", lojas: rows.map(r => r.perfil) });
  } catch (e) { res.status(500).json({ erro: e.message }); }
});

// ── API Posts ──────────────────────────────────────────────────
app.get("/api/dados", async (req, res) => {
  if (!pool) return res.json([]);
  try {
    const [rows] = await pool.query("SELECT * FROM posts ORDER BY created_at DESC LIMIT 500");
    const result = rows.map(r => {
      const d = { ...r };
      try { d.keywords = JSON.parse(d.keywords || "[]"); } catch(e){ d.keywords = []; }
      return d;
    });
    res.json(result);
  } catch (e) { console.error(e); res.json([]); }
});

app.post("/api/posts/add", async (req, res) => {
  if (!pool) return res.status(503).json({ erro: "Banco indisponível" });
  const data = req.body || {};
  const postId = data.id || `ext_${Date.now()}`;
  
  // Se veio imagem em Base64, transforma em arquivo e guarda o link curto
  const finalImage = salvarImagemB64(postId, data.image || "");

  try {
    await pool.query(`
      INSERT INTO posts (id, tipo, store, title, description, price, image, url, date, likes, keywords)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON DUPLICATE KEY UPDATE 
        title=VALUES(title), description=VALUES(description), price=VALUES(price), 
        image=VALUES(image), date=VALUES(date), keywords=VALUES(keywords)
    `, [
      postId, data.tipo || 'post', data.store, data.title, data.description, 
      data.price, finalImage, data.url, data.date, data.likes || 0, 
      JSON.stringify(data.keywords || [])
    ]);
    res.status(201).json({ msg: "OK", id: postId });
  } catch (e) { res.status(500).json({ erro: e.message }); }
});

app.post("/api/posts/sync", async (req, res) => {
  if (!pool) return res.status(503).json({ erro: "Banco indisponível" });
  const lista = req.body;
  if (!Array.isArray(lista)) return res.status(400).json({ erro: "Formato inválido" });

  let sucessos = 0;
  for (const post of lista) {
    try {
      const finalImage = salvarImagemB64(post.id, post.image || "");
      await pool.query(`
        INSERT INTO posts (id, tipo, store, title, description, price, image, url, date, likes, keywords)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE 
          title=VALUES(title), description=VALUES(description), price=VALUES(price), 
          image=VALUES(image), date=VALUES(date), keywords=VALUES(keywords)
      `, [
        post.id, post.tipo || 'post', post.store, post.title, post.description, 
        post.price || 'Consulte', finalImage, post.url, post.date, post.likes || 0, 
        JSON.stringify(post.keywords || [])
      ]);
      sucessos++;
    } catch (e) { console.error("Erro sync item:", e.message); }
  }
  res.json({ msg: `${sucessos} posts sincronizados` });
});

app.get("/api/status", (req, res) => {
  res.json({ rodando: true, db: "MySQL" });
});

// ── Start ──────────────────────────────────────────────────────
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`� Servidor MySQL Repasse na porta ${PORT}`);
  initDb().catch(console.error);
});
