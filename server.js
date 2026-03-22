const express = require("express");
const mysql = require("mysql2/promise");
const fs = require("fs");
const path = require("path");
const cors = require("cors");
const app = express();
const PORT = process.env.PORT || 3000;

// Configuração de Pastas
const IMAGENS_DIR = path.join(__dirname, "imagens");
if (!fs.existsSync(IMAGENS_DIR)) fs.mkdirSync(IMAGENS_DIR, { recursive: true });

app.use(cors());
app.use(express.json({ limit: "100mb" }));
app.use("/api/imagens", express.static(IMAGENS_DIR));
app.use(express.static(path.join(__dirname))); // Serve os arquivos HTML/JS da pasta raiz

// Banco de Dados Hostinger
const DB_CONFIG = {
  host: "127.0.0.1",
  user: "u221220547_jonatancgi",
  password: "2Art9Cm#TUxYUC6",
  database: "u221220547_jcmotors",
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
};

const pool = mysql.createPool(DB_CONFIG);

async function init() {
  try {
    const conn = await pool.getConnection();
    await conn.query(`CREATE TABLE IF NOT EXISTS posts (
      id VARCHAR(100) PRIMARY KEY, tipo VARCHAR(50), store VARCHAR(100), title TEXT,
      description TEXT, price VARCHAR(50), image TEXT, url TEXT,
      date DATETIME, likes INT DEFAULT 0, keywords TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`);
    conn.release();
    console.log("Banco MySQL OK");
    return true;
  } catch (e) {
    console.error("Erro no Banco:", e.message);
    return false;
  }
}

// Rotas API
app.get("/api/admin/init", async (req, res) => {
  const ok = await init();
  res.json({ ok, msg: ok ? "Tabelas prontas" : "Erro ao criar tabelas" });
});

app.post("/api/posts/sync", async (req, res) => {
  const list = req.body;
  let ok = 0;
  let errors = [];

  for (const p of list) {
    try {
      const imgPath = saveImg(p.id, p.image);
      await pool.query(
        `INSERT INTO posts (id, tipo, store, title, description, price, image, url, date, likes, keywords)
         VALUES (?,?,?,?,?,?,?,?,?,?,?) 
         ON DUPLICATE KEY UPDATE title=VALUES(title), price=VALUES(price), image=VALUES(image)`,
        [p.id, p.tipo, p.store, p.title, p.description, p.price, imgPath, p.url, p.date || new Date(), p.likes || 0, JSON.stringify(p.keywords || [])]
      );
      ok++;
    } catch (e) {
      errors.push(e.message);
    }
  }
  res.json({ msg: `${ok} posts ok`, errors: errors.slice(0, 5) });
});

app.get("/api/posts", async (req, res) => {
  try {
    const [rows] = await pool.query("SELECT * FROM posts ORDER BY date DESC LIMIT 200");
    res.json(rows);
  } catch (e) {
    res.status(500).json({ err: e.message });
  }
});

// Funções Auxiliares
function saveImg(id, base64) {
  if (!base64 || !base64.includes("base64,")) return base64;
  try {
    const buffer = Buffer.from(base64.split(",")[1], "base64");
    const filename = `img_${id.replace(/\W/g, "_")}.jpg`;
    fs.writeFileSync(path.join(IMAGENS_DIR, filename), buffer);
    return `/api/imagens/${filename}`;
  } catch (e) {
    return base64;
  }
}

// Página Inicial (Telas de volta)
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

app.listen(PORT, () => {
  console.log(`Server ON na porta ${PORT}`);
  init();
});
