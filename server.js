const express = require("express");
const mysql = require("mysql2/promise");
const fs = require("fs");
const path = require("path");
const cors = require("cors");
const app = express();
const PORT = process.env.PORT || 3000;
const IMAGENS_DIR = path.join(__dirname, "imagens");
if (!fs.existsSync(IMAGENS_DIR)) fs.mkdirSync(IMAGENS_DIR, { recursive: true });
app.use(cors());
app.use(express.json({ limit: "50mb" }));
app.use("/api/imagens", express.static(IMAGENS_DIR));
const DB = {
  host: "localhost",
  user: "u221220547_jonatancgi",
  password: "2Art9Cm#TUxYUC6",
  database: "u221220547_jcmotors",
  waitForConnections: true, connectionLimit: 5
};
const pool = mysql.createPool(DB);
async function init() {
  try {
    await pool.query(`CREATE TABLE IF NOT EXISTS posts (
      id VARCHAR(100) PRIMARY KEY, tipo VARCHAR(50), store VARCHAR(100), title TEXT,
      description TEXT, price VARCHAR(50), image TEXT, url TEXT,
      date DATETIME, likes INT DEFAULT 0, keywords TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`); return true;
  } catch (e) { console.error("Erro no INIT:", e); return false; }
}

app.get("/", (req, res) => {
  res.send("🚀 SERVIDOR ATUALIZADO 22/03 - BANCO OK");
});

app.get("/api/admin/init", async (req, res) => {
  const ok = await init(); res.json({ ok });
});

app.post("/api/posts/sync", async (req, res) => {
  const list = req.body; let ok = 0, err = [];
  for (const p of list) {
    try {
      const img = saveImg(p.id, p.image);
      await pool.query(`INSERT INTO posts (id, tipo, store, title, description, price, image, url, date, likes, keywords)
        VALUES (?,?,?,?,?,?,?,?,?,?,?) ON DUPLICATE KEY UPDATE title=VALUES(title), price=VALUES(price), image=VALUES(image)`,
        [p.id, p.tipo, p.store, p.title, p.description, p.price, img, p.url, p.date || new Date(), p.likes || 0, JSON.stringify(p.keywords || [])]
      ); ok++;
    } catch (e) { err.push(e.message); }
  }
  res.json({ msg: `${ok} posts ok`, errors: err.slice(0, 5) });
});

function saveImg(id, b) {
  if (!b || !b.includes("base64,")) return b;
  try {
    const buf = Buffer.from(b.split(",")[1], "base64");
    const name = `img_${id.replace(/\W/g, "_")}.jpg`;
    fs.writeFileSync(path.join(IMAGENS_DIR, name), buf);
    return `/api/imagens/${name}`;
  } catch (e) { return b; }
}

app.get("/api/posts", async (req, res) => {
  try {
    const [rows] = await pool.query("SELECT * FROM posts ORDER BY date DESC LIMIT 100");
    res.json(rows);
  } catch (e) { res.status(500).json({ err: e.message }); }
});

app.listen(PORT, () => { console.log("Server ON"); init(); });
