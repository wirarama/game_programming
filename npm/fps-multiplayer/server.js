/**
 * Server multiplayer FPS sederhana.
 * - HTTP server statis untuk melayani folder /public (client raycaster).
 * - WebSocket server untuk sinkronisasi posisi pemain, tembakan, HP, kill/death.
 *
 * Jalankan:
 *   npm install
 *   npm start
 * Lalu buka http://localhost:3000 (pemain lain buka IP LAN kamu di port yang sama).
 */

const http = require("http");
const fs = require("fs");
const path = require("path");
const { WebSocketServer } = require("ws");

const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname, "public");

// ---------------------------------------------------------------
// PETA DUNIA (harus identik dengan MAP di public/game.js)
// ---------------------------------------------------------------
const MAP = [
  "1111111111111111",
  "1000000000000001",
  "1011110111101101",
  "1010000100001001",
  "1010111101011101",
  "1000100000010001",
  "1110100111010111",
  "1000100100010001",
  "1011101101110101",
  "1000001000000101",
  "1111111111111111",
];
const MAP_W = MAP[0].length;
const MAP_H = MAP.length;

function isWall(x, y) {
  const ix = Math.floor(x);
  const iy = Math.floor(y);
  if (ix < 0 || iy < 0 || ix >= MAP_W || iy >= MAP_H) return true;
  return MAP[iy][ix] === "1";
}

const SPAWN_POINTS = [
  { x: 2.5, y: 2.5 },
  { x: 14.5, y: 2.5 },
  { x: 2.5, y: 8.5 },
  { x: 14.5, y: 8.5 },
  { x: 8.5, y: 8.5 },
  { x: 8.5, y: 2.5 },
];

const COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6", "#1abc9c", "#e67e22", "#ecf0f1"];

const MAX_HP = 100;
const SHOOT_RANGE = 20;
const SHOOT_HALF_ANGLE = 0.08; // toleransi arah tembak (radian)
const SHOOT_DAMAGE = 20;
const RESPAWN_MS = 3000;
const TICK_HZ = 20;

// ---------------------------------------------------------------
// STATE
// ---------------------------------------------------------------
/** @type {Map<string, any>} */
const players = new Map();
let nextId = 1;
let colorIdx = 0;

function randomSpawn() {
  return SPAWN_POINTS[Math.floor(Math.random() * SPAWN_POINTS.length)];
}

function spawnPlayer(id, name) {
  const spawn = randomSpawn();
  return {
    id,
    name: name || `Player${id}`,
    color: COLORS[colorIdx++ % COLORS.length],
    x: spawn.x,
    y: spawn.y,
    angle: 0,
    hp: MAX_HP,
    alive: true,
    kills: 0,
    deaths: 0,
    lastShotAt: 0,
  };
}

function publicState() {
  const arr = [];
  for (const p of players.values()) {
    arr.push({
      id: p.id,
      name: p.name,
      color: p.color,
      x: p.x,
      y: p.y,
      angle: p.angle,
      hp: p.hp,
      alive: p.alive,
      kills: p.kills,
      deaths: p.deaths,
    });
  }
  return arr;
}

// ---------------------------------------------------------------
// HTTP STATIS
// ---------------------------------------------------------------
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json",
};

const server = http.createServer((req, res) => {
  let reqPath = decodeURIComponent(req.url.split("?")[0]);
  if (reqPath === "/") reqPath = "/index.html";
  const filePath = path.join(PUBLIC_DIR, reqPath);

  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403);
    return res.end("Forbidden");
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { "Content-Type": "text/plain" });
      return res.end("404 Not Found");
    }
    const ext = path.extname(filePath);
    res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
    res.end(data);
  });
});

// ---------------------------------------------------------------
// WEBSOCKET
// ---------------------------------------------------------------
const wss = new WebSocketServer({ server });

function broadcast(obj, exceptId = null) {
  const msg = JSON.stringify(obj);
  for (const ws of wss.clients) {
    if (ws.readyState === ws.OPEN && ws.playerId !== exceptId) {
      ws.send(msg);
    }
  }
}

function broadcastAll(obj) {
  const msg = JSON.stringify(obj);
  for (const ws of wss.clients) {
    if (ws.readyState === ws.OPEN) ws.send(msg);
  }
}

wss.on("connection", (ws) => {
  const id = String(nextId++);
  ws.playerId = id;

  wss.on("close", () => {});

  ws.on("message", (raw) => {
    let msg;
    try {
      msg = JSON.parse(raw);
    } catch (e) {
      return;
    }

    switch (msg.type) {
      case "join": {
        const player = spawnPlayer(id, (msg.name || "").slice(0, 16));
        players.set(id, player);
        ws.send(
          JSON.stringify({
            type: "init",
            id,
            map: MAP,
            you: player,
            players: publicState(),
          })
        );
        broadcast({ type: "player_joined", player }, id);
        break;
      }

      case "move": {
        const p = players.get(id);
        if (!p || !p.alive) return;
        const { x, y, angle } = msg;
        if (typeof x !== "number" || typeof y !== "number" || typeof angle !== "number") return;
        // validasi anti-cheat sederhana: tolak posisi yang jatuh di dalam dinding
        // atau lompatan jarak yang tidak wajar dalam satu tick.
        const dist = Math.hypot(x - p.x, y - p.y);
        if (dist > 1.5) return; // lompatan terlalu jauh, abaikan
        if (!isWall(x, y)) {
          p.x = x;
          p.y = y;
        }
        p.angle = angle;
        break;
      }

      case "shoot": {
        const shooter = players.get(id);
        if (!shooter || !shooter.alive) return;
        const now = Date.now();
        if (now - shooter.lastShotAt < 250) return; // rate limit
        shooter.lastShotAt = now;

        broadcast({ type: "shot_fx", id }, null);

        // cari target terdekat dalam arah tembak yang tidak terhalang dinding
        let bestTarget = null;
        let bestDist = SHOOT_RANGE;
        for (const target of players.values()) {
          if (target.id === id || !target.alive) continue;
          const dx = target.x - shooter.x;
          const dy = target.y - shooter.y;
          const dist = Math.hypot(dx, dy);
          if (dist > SHOOT_RANGE) continue;
          let angleTo = Math.atan2(dy, dx) - shooter.angle;
          angleTo = ((angleTo + Math.PI) % (2 * Math.PI)) - Math.PI;
          if (Math.abs(angleTo) > SHOOT_HALF_ANGLE) continue;

          // cek terhalang tembok sepanjang garis tembak
          let blocked = false;
          const steps = Math.ceil(dist / 0.05);
          for (let s = 1; s < steps; s++) {
            const t = (s / steps) * dist;
            if (isWall(shooter.x + Math.cos(shooter.angle) * t, shooter.y + Math.sin(shooter.angle) * t)) {
              blocked = true;
              break;
            }
          }
          if (!blocked && dist < bestDist) {
            bestDist = dist;
            bestTarget = target;
          }
        }

        if (bestTarget) {
          bestTarget.hp -= SHOOT_DAMAGE;
          broadcastAll({ type: "hit", targetId: bestTarget.id, shooterId: id, hp: Math.max(0, bestTarget.hp) });
          if (bestTarget.hp <= 0) {
            bestTarget.alive = false;
            bestTarget.deaths += 1;
            shooter.kills += 1;
            broadcastAll({
              type: "death",
              targetId: bestTarget.id,
              shooterId: id,
              kills: shooter.kills,
              deaths: bestTarget.deaths,
            });
            setTimeout(() => {
              if (!players.has(bestTarget.id)) return;
              const spawn = randomSpawn();
              bestTarget.x = spawn.x;
              bestTarget.y = spawn.y;
              bestTarget.hp = MAX_HP;
              bestTarget.alive = true;
              broadcastAll({ type: "respawn", id: bestTarget.id, x: bestTarget.x, y: bestTarget.y });
            }, RESPAWN_MS);
          }
        }
        break;
      }

      default:
        break;
    }
  });

  ws.on("close", () => {
    players.delete(id);
    broadcast({ type: "player_left", id }, id);
  });
});

// broadcast state posisi semua pemain secara berkala
setInterval(() => {
  if (players.size === 0) return;
  broadcastAll({ type: "state", players: publicState() });
}, 1000 / TICK_HZ);

server.listen(PORT, () => {
  console.log(`FPS multiplayer server jalan di http://localhost:${PORT}`);
});
