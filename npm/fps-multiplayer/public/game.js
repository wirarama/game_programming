/**
 * Client FPS multiplayer - raycaster 2.5D di atas <canvas>, sinkron lewat WebSocket.
 */

// ---------------------------------------------------------------
// KONFIGURASI & PETA (harus sama dengan server.js)
// ---------------------------------------------------------------
const MAP_FALLBACK = [
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

const WIDTH = 900, HEIGHT = 600;
const HALF_H = HEIGHT / 2;
const FOV = Math.PI / 3;
const NUM_RAYS = Math.floor(WIDTH / 2);
const MAX_DEPTH = 20;
const DELTA_ANGLE = FOV / NUM_RAYS;
const DIST = NUM_RAYS / (2 * Math.tan(FOV / 2));
const SCALE = WIDTH / NUM_RAYS;
const MOVE_SPEED = 0.06;
const ROT_SPEED = 0.0025;

let MAP = MAP_FALLBACK;
let MAP_W = MAP[0].length, MAP_H = MAP.length;

function isWall(x, y) {
  const ix = Math.floor(x), iy = Math.floor(y);
  if (ix < 0 || iy < 0 || ix >= MAP_W || iy >= MAP_H) return true;
  return MAP[iy][ix] === "1";
}

// ---------------------------------------------------------------
// STATE LOKAL
// ---------------------------------------------------------------
const canvas = document.getElementById("game");
canvas.width = WIDTH;
canvas.height = HEIGHT;
const ctx = canvas.getContext("2d");

let ws = null;
let myId = null;
let me = { x: 2.5, y: 2.5, angle: 0, hp: 100, alive: true, kills: 0, deaths: 0, color: "#e74c3c" };
/** id -> player state dari server (termasuk diri sendiri untuk skor) */
let remotePlayers = new Map();
let shootFxFrom = new Set(); // id pemain yang baru saja menembak (muzzle flash)
let shootTimer = 0;
let lastShotSent = 0;

const keys = {};
let mouseDX = 0;
let pointerLocked = false;

const statusEl = document.getElementById("status");
const scoreboardEl = document.getElementById("scoreboard");
const killfeedEl = document.getElementById("killfeed");
const hpBar = document.getElementById("hp-bar");
const deathscreen = document.getElementById("deathscreen");

// ---------------------------------------------------------------
// KONEKSI WEBSOCKET
// ---------------------------------------------------------------
function connect(name) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}`);

  ws.onopen = () => {
    ws.send(JSON.stringify({ type: "join", name }));
    statusEl.textContent = "Terhubung ke server";
  };

  ws.onclose = () => {
    statusEl.textContent = "Koneksi terputus. Muat ulang halaman untuk mencoba lagi.";
  };

  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    switch (msg.type) {
      case "init": {
        myId = msg.id;
        MAP = msg.map;
        MAP_W = MAP[0].length;
        MAP_H = MAP.length;
        me = { ...msg.you };
        remotePlayers.clear();
        for (const p of msg.players) remotePlayers.set(p.id, p);
        remotePlayers.set(myId, me);
        break;
      }
      case "player_joined": {
        remotePlayers.set(msg.player.id, msg.player);
        addKillFeed(`${msg.player.name} bergabung`);
        break;
      }
      case "player_left": {
        const p = remotePlayers.get(msg.id);
        if (p) addKillFeed(`${p.name} keluar`);
        remotePlayers.delete(msg.id);
        break;
      }
      case "state": {
        for (const p of msg.players) {
          if (p.id === myId) {
            // server adalah otoritas untuk hp/kills/deaths/alive; posisi tetap client-predicted
            me.hp = p.hp;
            me.alive = p.alive;
            me.kills = p.kills;
            me.deaths = p.deaths;
            remotePlayers.set(myId, me);
          } else {
            remotePlayers.set(p.id, p);
          }
        }
        renderScoreboard();
        break;
      }
      case "shot_fx": {
        shootFxFrom.add(msg.id);
        setTimeout(() => shootFxFrom.delete(msg.id), 100);
        break;
      }
      case "hit": {
        if (msg.targetId === myId) {
          me.hp = msg.hp;
          flashDamage();
        }
        break;
      }
      case "death": {
        const shooter = remotePlayers.get(msg.shooterId);
        const target = remotePlayers.get(msg.targetId);
        const shooterName = shooter ? shooter.name : "???";
        const targetName = target ? target.name : "???";
        addKillFeed(`${shooterName} mengalahkan ${targetName}`);
        if (msg.targetId === myId) {
          me.alive = false;
          deathscreen.style.display = "flex";
        }
        break;
      }
      case "respawn": {
        if (msg.id === myId) {
          me.x = msg.x;
          me.y = msg.y;
          me.hp = 100;
          me.alive = true;
          deathscreen.style.display = "none";
        }
        const p = remotePlayers.get(msg.id);
        if (p) {
          p.x = msg.x;
          p.y = msg.y;
          p.hp = 100;
          p.alive = true;
        }
        break;
      }
    }
  };
}

function addKillFeed(text) {
  const div = document.createElement("div");
  div.textContent = text;
  killfeedEl.appendChild(div);
  setTimeout(() => div.remove(), 4000);
}

let damageFlashTimer = 0;
function flashDamage() {
  damageFlashTimer = 10;
}

// ---------------------------------------------------------------
// INPUT
// ---------------------------------------------------------------
window.addEventListener("keydown", (e) => (keys[e.code] = true));
window.addEventListener("keyup", (e) => (keys[e.code] = false));

canvas.addEventListener("click", () => {
  if (!pointerLocked) {
    canvas.requestPointerLock();
  } else if (me.alive) {
    tryShoot();
  }
});

document.addEventListener("pointerlockchange", () => {
  pointerLocked = document.pointerLockElement === canvas;
});

document.addEventListener("mousemove", (e) => {
  if (pointerLocked) mouseDX += e.movementX;
});

function tryShoot() {
  const now = performance.now();
  if (now - lastShotSent < 250) return;
  lastShotSent = now;
  shootTimer = 6;
  ws.send(JSON.stringify({ type: "shoot" }));
}

// ---------------------------------------------------------------
// UPDATE LOKAL (movement prediction)
// ---------------------------------------------------------------
function update() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;

  me.angle += mouseDX * ROT_SPEED;
  me.angle = ((me.angle % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
  mouseDX = 0;

  if (me.alive) {
    let dx = 0, dy = 0;
    const speed = MOVE_SPEED;
    if (keys["KeyW"]) { dx += Math.cos(me.angle) * speed; dy += Math.sin(me.angle) * speed; }
    if (keys["KeyS"]) { dx -= Math.cos(me.angle) * speed; dy -= Math.sin(me.angle) * speed; }
    if (keys["KeyA"]) { dx += Math.cos(me.angle - Math.PI / 2) * speed; dy += Math.sin(me.angle - Math.PI / 2) * speed; }
    if (keys["KeyD"]) { dx += Math.cos(me.angle + Math.PI / 2) * speed; dy += Math.sin(me.angle + Math.PI / 2) * speed; }

    const margin = 0.2;
    if (!isWall(me.x + dx + Math.sign(dx) * margin, me.y)) me.x += dx;
    if (!isWall(me.x, me.y + dy + Math.sign(dy) * margin)) me.y += dy;
  }

  ws.send(JSON.stringify({ type: "move", x: me.x, y: me.y, angle: me.angle }));

  if (shootTimer > 0) shootTimer--;
  if (damageFlashTimer > 0) damageFlashTimer--;
}

// ---------------------------------------------------------------
// RENDER
// ---------------------------------------------------------------
function castRays() {
  ctx.fillStyle = "#3c3c5a";
  ctx.fillRect(0, 0, WIDTH, HALF_H);
  ctx.fillStyle = "#464646";
  ctx.fillRect(0, HALF_H, WIDTH, HALF_H);

  const depthBuffer = new Array(NUM_RAYS).fill(MAX_DEPTH);
  const startAngle = me.angle - FOV / 2;

  for (let ray = 0; ray < NUM_RAYS; ray++) {
    const angle = startAngle + ray * DELTA_ANGLE;
    const sinA = Math.sin(angle), cosA = Math.cos(angle);
    let depth = 0;
    const step = 0.02;
    let hit = false;
    while (depth < MAX_DEPTH) {
      depth += step;
      const tx = me.x + cosA * depth;
      const ty = me.y + sinA * depth;
      if (isWall(tx, ty)) { hit = true; break; }
    }
    if (hit) {
      depth *= Math.cos(me.angle - angle);
      depth = Math.max(depth, 0.0001);
      depthBuffer[ray] = depth;
      const wallH = Math.min(HEIGHT, DIST / depth);
      const shade = Math.max(30, 255 - depth * 20);
      ctx.fillStyle = `rgb(${shade}, ${shade * 0.55}, ${shade * 0.55})`;
      const x = ray * SCALE;
      ctx.fillRect(x, HALF_H - wallH / 2, SCALE + 1, wallH);
    }
  }
  return depthBuffer;
}

function drawSprites(depthBuffer) {
  const others = [];
  for (const p of remotePlayers.values()) {
    if (p.id === myId || !p.alive) continue;
    others.push(p);
  }
  others.sort((a, b) => {
    const da = (a.x - me.x) ** 2 + (a.y - me.y) ** 2;
    const db = (b.x - me.x) ** 2 + (b.y - me.y) ** 2;
    return db - da;
  });

  for (const p of others) {
    const dx = p.x - me.x, dy = p.y - me.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 0.3) continue;
    let angleTo = Math.atan2(dy, dx) - me.angle;
    angleTo = ((angleTo + Math.PI) % (2 * Math.PI)) - Math.PI;
    if (Math.abs(angleTo) > FOV / 2 + 0.3) continue;

    const projDist = dist * Math.cos(angleTo);
    if (projDist < 0.1) continue;

    const screenX = (0.5 + angleTo / FOV) * WIDTH;
    const size = Math.min(HEIGHT, (DIST / projDist) * 0.6);

    const rayIdx = Math.floor(screenX / SCALE);
    if (rayIdx >= 0 && rayIdx < NUM_RAYS && projDist > depthBuffer[rayIdx] + 0.2) continue;

    const left = screenX - size / 2, top = HALF_H - size / 2;

    ctx.fillStyle = p.color || "#e74c3c";
    ctx.fillRect(left, top, size, size);
    ctx.strokeStyle = "rgba(0,0,0,0.6)";
    ctx.lineWidth = 3;
    ctx.strokeRect(left, top, size, size);

    if (shootFxFrom.has(p.id)) {
      ctx.fillStyle = "rgba(255,230,100,0.9)";
      ctx.beginPath();
      ctx.arc(screenX, top - 10, 10, 0, Math.PI * 2);
      ctx.fill();
    }

    // nametag + hp bar
    ctx.font = "13px Consolas, monospace";
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.fillText(p.name, screenX, top - 18);
    const hpRatio = Math.max(0, p.hp / 100);
    ctx.fillStyle = "#000";
    ctx.fillRect(left, top - 12, size, 5);
    ctx.fillStyle = "#2ecc71";
    ctx.fillRect(left, top - 12, size * hpRatio, 5);
  }
}

function drawGun() {
  const gw = 170, gh = 170;
  const x = WIDTH / 2 - gw / 2;
  const y = HEIGHT - gh + (shootTimer > 0 ? 10 : 0);
  ctx.fillStyle = "#4a4a4a";
  roundRect(x, y, gw, gh, 12);
  ctx.fillStyle = "#1f1f1f";
  roundRect(x + 58, y - 20, 55, 40, 6);
  if (shootTimer > 0) {
    ctx.fillStyle = "rgba(255,230,100,0.95)";
    ctx.beginPath();
    ctx.arc(WIDTH / 2, y - 15, 26, 0, Math.PI * 2);
    ctx.fill();
  }
}

function roundRect(x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
  ctx.fill();
}

function drawCrosshair() {
  const cx = WIDTH / 2, cy = HEIGHT / 2;
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cx - 9, cy); ctx.lineTo(cx + 9, cy);
  ctx.moveTo(cx, cy - 9); ctx.lineTo(cx, cy + 9);
  ctx.stroke();
}

function drawMinimap() {
  const scale = 7;
  const ox = WIDTH - MAP_W * scale - 12, oy = HEIGHT - MAP_H * scale - 12;
  for (let row = 0; row < MAP_H; row++) {
    for (let col = 0; col < MAP_W; col++) {
      ctx.fillStyle = MAP[row][col] === "1" ? "#969696" : "#1e1e1e";
      ctx.fillRect(ox + col * scale, oy + row * scale, scale, scale);
    }
  }
  for (const p of remotePlayers.values()) {
    if (!p.alive) continue;
    ctx.fillStyle = p.id === myId ? "#2ecc71" : (p.color || "#e74c3c");
    ctx.beginPath();
    ctx.arc(ox + p.x * scale, oy + p.y * scale, 3, 0, Math.PI * 2);
    ctx.fill();
  }
}

function renderScoreboard() {
  const list = [...remotePlayers.values()].sort((a, b) => b.kills - a.kills);
  scoreboardEl.innerHTML = "<b>Skor</b><br>" + list
    .map((p) => `<div>${p.id === myId ? "➤ " : ""}${escapeHtml(p.name)} — ${p.kills}K / ${p.deaths}D</div>`)
    .join("");
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function render() {
  const depthBuffer = castRays();
  drawSprites(depthBuffer);
  drawGun();
  drawCrosshair();
  drawMinimap();

  if (damageFlashTimer > 0) {
    ctx.fillStyle = `rgba(255,0,0,${damageFlashTimer / 30})`;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
  }

  hpBar.style.width = `${Math.max(0, me.hp)}%`;
}

// ---------------------------------------------------------------
// LOOP UTAMA
// ---------------------------------------------------------------
function loop() {
  update();
  render();
  requestAnimationFrame(loop);
}

// ---------------------------------------------------------------
// UI: LAYAR JOIN
// ---------------------------------------------------------------
document.getElementById("joinBtn").addEventListener("click", startGame);
document.getElementById("nameInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") startGame();
});

function startGame() {
  const name = document.getElementById("nameInput").value.trim() || `Player${Math.floor(Math.random() * 1000)}`;
  document.getElementById("join").style.display = "none";
  connect(name);
  canvas.requestPointerLock();
  requestAnimationFrame(loop);
}
