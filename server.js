const express = require("express");
const mysql = require("mysql2/promise");
const fs = require("fs");
const path = require("path");
const cors = require("cors");
const app = express();
const PORT = process.env.PORT || 3000;

// Configuração de Pastas (Caminho absoluto robusto)
const IMAGENS_DIR = path.resolve(__dirname, "imagens");
if (!fs.existsSync(IMAGENS_DIR)) {
  fs.mkdirSync(IMAGENS_DIR, { recursive: true });
  console.log("Criei a pasta imagens em:", IMAGENS_DIR);
}

app.use(cors());
app.use(express.json({ limit: "150mb" }));

// Rota de Imagens (IMPORTANTE: Deve vir antes das outras)
app.use("/api/imagens", express.static(IMAGENS_DIR));
app.use(express.static(path.resolve(__dirname)));

const DB_CONFIG = {
  host: "127.0.0.1",
  user: "u221220547_jonatancgi",
  password: "2Art9Cm#TUxYUC6",
  database: "u221220547_jcmotors",
  waitForConnections: true,
  connectionLimit: 10
};

const pool = mysql.createPool(DB_CONFIG);

// Alias para compatibilidade com frotend velho
app.get("/api/dados", async (req, res) => {
  try {
    const [rows] = await pool.query("SELECT * FROM posts ORDER BY date DESC LIMIT 500");
    res.json(rows);
  } catch (e) { res.status(500).json({ err: e.message }); }
});

app.get("/api/lojas", (req, res) => {
  res.json(["repassesgr", "cwb.repasse_", "autopar.repasses", "ml_repasses", "parana_repasses"]);
});

app.get("/api/status", (req, res) => {
  res.json({ rodando: false, total_posts: 450, ultima_coleta: new Date().toLocaleString() });
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
    } catch (e) { errors.push(e.message); }
  }
  res.json({ msg: `${ok} posts ok`, errors: errors.slice(0, 5) });
});

app.get("/api/posts", async (req, res) => {
  try {
    const [rows] = await pool.query("SELECT * FROM posts ORDER BY date DESC LIMIT 500");
    res.json(rows);
  } catch (e) { res.status(500).json({ err: e.message }); }
});

function saveImg(id, base64) {
  if (!base64 || !base64.includes("base64,")) return base64;
  try {
    const buffer = Buffer.from(base64.split(",")[1], "base64");
    const filename = `img_${id.replace(/\W/g, "_")}.jpg`;
    const fullPath = path.join(IMAGENS_DIR, filename);
    fs.writeFileSync(fullPath, buffer);
    return `/api/imagens/${filename}`;
  } catch (e) {
    console.error("Erro ao salvar imagem:", e.message);
    return base64;
  }
}

app.get("/", (req, res) => {
  res.sendFile(path.resolve(__dirname, "index.html"));
});

app.listen(PORT, () => {
  console.log("Server running on port", PORT);
});
