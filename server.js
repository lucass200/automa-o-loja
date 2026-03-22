const express = require("express");
const mysql = require("mysql2/promise");
const fs = require("fs");
const path = require("path");
const cors = require("cors");
const axios = require("axios"); // Para baixar imagens de URLs
const app = express();
const PORT = process.env.PORT || 3000;

// Configuração de Pastas
const IMAGENS_DIR = path.resolve(process.cwd(), "imagens");
if (!fs.existsSync(IMAGENS_DIR)) fs.mkdirSync(IMAGENS_DIR, { recursive: true });

app.use(cors());
app.use(express.json({ limit: "200mb" }));

// ROTA MANUAL DE IMAGENS 
app.get("/api/imagens/:name", (req, res) => {
  const file = path.join(IMAGENS_DIR, req.params.name);
  if (fs.existsSync(file)) res.sendFile(file);
  else res.status(404).send("404: Arquivo sumiu do disco");
});

// BANCO DE DADOS
const DB_CONFIG = {
  host: "127.0.0.1",
  user: "u221220547_jonatancgi",
  password: "2Art9Cm#TUxYUC6",
  database: "u221220547_jcmotors",
  waitForConnections: true,
  connectionLimit: 10
};
const pool = mysql.createPool(DB_CONFIG);

// Inicializa Tabelas
async function init() {
  try {
    const conn = await pool.getConnection();
    await conn.query(`CREATE TABLE IF NOT EXISTS posts (
      id VARCHAR(100) PRIMARY KEY, tipo VARCHAR(50), store VARCHAR(100), title TEXT,
      description TEXT, price VARCHAR(50), image TEXT, url TEXT,
      date DATETIME, likes INT DEFAULT 0, keywords TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`);
    await conn.query(`CREATE TABLE IF NOT EXISTS lojas (perfil VARCHAR(100) PRIMARY KEY)`);
    conn.release();
  } catch (e) { console.error(e.message); }
}

// LOGICA DE SALVAR IMAGEM (Base64 ou URL)
async function saveImg(id, source) {
  if (!source) return source;
  const filename = `img_${id.replace(/\W/g, "_")}.jpg`;
  const fullPath = path.join(IMAGENS_DIR, filename);

  // Caso 1: É Base64
  if (source.includes("base64,")) {
    try {
      const buffer = Buffer.from(source.split(",")[1], "base64");
      fs.writeFileSync(fullPath, buffer);
      return `/api/imagens/${filename}`;
    } catch (e) { return source; }
  }

  // Caso 2: É uma URL externa (Instagram, etc)
  if (source.startsWith("http")) {
    try {
      const resp = await axios.get(source, { responseType: 'arraybuffer' });
      fs.writeFileSync(fullPath, resp.data);
      return `/api/imagens/${filename}`;
    } catch (e) { return source; } // Se falhar download, usa o link direto
  }

  return source;
}

// SYNC
app.post("/api/posts/sync", async (req, res) => {
  const list = req.body;
  let ok = 0;
  for (const p of list) {
    try {
      const imgPath = await saveImg(p.id, p.image);
      await pool.query(
        `INSERT INTO posts (id, tipo, store, title, description, price, image, url, date, likes, keywords)
         VALUES (?,?,?,?,?,?,?,?,?,?,?) ON DUPLICATE KEY UPDATE title=VALUES(title), price=VALUES(price), image=VALUES(image)`,
        [p.id, p.tipo, p.store, p.title, p.description, p.price, imgPath, p.url, p.date || new Date(), p.likes || 0, JSON.stringify(p.keywords || [])]
      );
      ok++;
    } catch (e) { }
  }
  res.json({ msg: `${ok} posts ok` });
});

// RESTANTE DAS ROTAS
app.get("/api/lojas", async (req, res) => {
  try {
    const [rows] = await pool.query("SELECT perfil FROM lojas");
    res.json(rows.map(r => r.perfil));
  } catch (e) { res.json(["repassesgr", "cwb.repasse_", "autopar.repasses"]); }
});

app.post("/api/lojas/add", async (req, res) => {
  const { perfis } = req.body;
  for (let p of perfis) {
    const pcl = p.replace("@", "").trim();
    if (pcl) await pool.query("INSERT IGNORE INTO lojas (perfil) VALUES (?)", [pcl]);
  }
  const [rows] = await pool.query("SELECT perfil FROM lojas");
  res.json({ lojas: rows.map(r => r.perfil) });
});

app.get("/api/posts", async (req, res) => {
  const [rows] = await pool.query("SELECT * FROM posts ORDER BY date DESC LIMIT 400");
  res.json(rows);
});

app.get("/api/status", async (req, res) => {
  const [rows] = await pool.query("SELECT COUNT(*) as t FROM posts");
  res.json({ rodando: false, total_posts: rows[0].t, ultima_coleta: new Date().toLocaleString() });
});

app.use(express.static(process.cwd()));
app.get("*", (req, res) => { res.sendFile(path.resolve(process.cwd(), "index.html")); });

app.listen(PORT, () => { console.log("ON"); init(); });
