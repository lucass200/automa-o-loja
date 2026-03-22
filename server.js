const express = require("express");
const mysql = require("mysql2/promise");
const fs = require("fs");
const path = require("path");
const cors = require("cors");
const app = express();
const PORT = process.env.PORT || 3000;

// Configuração de Pastas
const IMAGENS_DIR = path.join(process.cwd(), "imagens");
if (!fs.existsSync(IMAGENS_DIR)) {
  try {
    fs.mkdirSync(IMAGENS_DIR, { recursive: true });
    // Tenta dar permissão total na pasta
    fs.chmodSync(IMAGENS_DIR, 0o777);
  } catch (e) {
    console.error("Falha ao criar pasta:", e.message);
  }
}

app.use(cors());
app.use(express.json({ limit: "200mb" }));

// Servir imagens estáticas
app.use("/api/imagens", express.static(IMAGENS_DIR));
app.use(express.static(path.join(process.cwd())));

const DB_CONFIG = {
  host: "127.0.0.1",
  user: "u221220547_jonatancgi",
  password: "2Art9Cm#TUxYUC6",
  database: "u221220547_jcmotors",
  waitForConnections: true,
  connectionLimit: 10
};
const pool = mysql.createPool(DB_CONFIG);

app.get("/api/dados", async (req, res) => {
  try {
    const [rows] = await pool.query("SELECT * FROM posts ORDER BY date DESC LIMIT 800");
    res.json(rows);
  } catch (e) { res.status(500).json({ err: e.message }); }
});

app.get("/api/lojas", (req, res) => {
  res.json(["repassesgr", "cwb.repasse_", "autopar.repasses", "ml_repasses", "parana_repasses"]);
});

// Sync com ERROS DETALHADOS
app.post("/api/posts/sync", async (req, res) => {
  const list = req.body;
  let ok = 0, errors = [];
  for (const p of list) {
    try {
      // Salva imagem ou retorna erro se falhar
      const imgRes = saveImg(p.id, p.image);
      if (imgRes.error) throw new Error(`Falha Imagem: ${imgRes.error}`);

      const imgPath = imgRes.path;
      await pool.query(
        `INSERT INTO posts (id, tipo, store, title, description, price, image, url, date, likes, keywords)
         VALUES (?,?,?,?,?,?,?,?,?,?,?) ON DUPLICATE KEY UPDATE title=VALUES(title), price=VALUES(price), image=VALUES(image)`,
        [p.id, p.tipo, p.store, p.title, p.description, p.price, imgPath, p.url, p.date || new Date(), p.likes || 0, JSON.stringify(p.keywords || [])]
      );
      ok++;
    } catch (e) { errors.push(`${p.id}: ${e.message}`); }
  }
  res.json({ msg: `${ok} posts ok`, errors: errors.slice(0, 5) });
});

function saveImg(id, base64) {
  if (!base64 || !base64.includes("base64,")) return { path: base64 };
  try {
    const buffer = Buffer.from(base64.split(",")[1], "base64");
    const filename = `img_${id.replace(/\W/g, "_")}.jpg`;
    const fullPath = path.join(IMAGENS_DIR, filename);

    fs.writeFileSync(fullPath, buffer);
    return { path: `/api/imagens/${filename}` };
  } catch (e) {
    return { path: base64, error: e.message };
  }
}

app.get("/api/posts", async (req, res) => {
  try {
    const [rows] = await pool.query("SELECT * FROM posts ORDER BY date DESC LIMIT 800");
    res.json(rows);
  } catch (e) { res.status(500).json({ err: e.message }); }
});

app.get("/", (req, res) => {
  res.sendFile(path.join(process.cwd(), "index.html"));
});

app.listen(PORT, () => { console.log("Server ON"); });
