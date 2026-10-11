/**
 * GAME 2D ACTION — game.js
 * ------------------------------------------------------------
 * Engine utama: fisika, entitas (pemain / musuh / boss / peluru),
 * data level, kamera, render, HUD, dan alur layar
 * (menu -> cerita awal -> main -> cerita akhir).
 *
 * Semua karakter digambar langsung lewat Canvas API (tidak pakai
 * file gambar sprite), jadi game ini langsung jalan tanpa aset
 * tambahan. Ubah fungsi-fungsi di bagian "RENDER SPRITE" bila
 * ingin mengganti tampilan karakter.
 *
 * Cara mengedit LEVEL (jurang, halangan, air, checkpoint, musuh):
 * lihat bagian "DATA LEVEL" di bawah ini.
 *
 * Cara mengedit CERITA / GAMBAR menu, awal & akhir: lihat file
 * story-data.js (terpisah supaya mudah diedit).
 */

// ============================================================
// KONFIGURASI DASAR
// ============================================================
const CANVAS_W = 960;
const CANVAS_H = 540;
const GROUND_Y = 420;               // posisi Y permukaan tanah
const GRAVITY = 1700;               // px/s^2
const JUMP_VELOCITY = -620;         // px/s (negatif = ke atas)
const WALK_SPEED = 160;             // px/s
const RUN_SPEED = 300;              // px/s
const WATER_SLOW = 0.45;            // pengali kecepatan di area air
const FALL_DEATH_Y = GROUND_Y + 260; // jatuh melewati ini di jurang = mati

const PLAYER_W = 34, PLAYER_H = 58;
const ENEMY_W = 34, ENEMY_H = 56;
const BOSS_W = 74, BOSS_H = 100;

const HIT_INVULN_TIME = 1.1;   // detik kebal setelah kena peluru
const MAX_HITS = 3;            // jumlah peluru sebelum mati
const BIG_ATTACK_MAX = 2;      // jumlah pakai serangan besar
const ENEMIES_TO_BEAT_FOR_BOSS = 10;

const BULLET_SPEED_PLAYER = 560;
const BULLET_SPEED_ENEMY = 260;
const BULLET_SPEED_BOSS = 300;
const PLAYER_SHOOT_COOLDOWN = 0.30;
const PLAYER_BIG_COOLDOWN = 0.20;
const ENEMY_DETECT_RANGE = 420;
const BOSS_HP_MAX = 20;
const BOSS_BULLET_DAMAGE = 1;
const BIG_ATTACK_DAMAGE = 5;

const WORLD_WIDTH = 5820;
const GATE_X = 4800;                // gerbang menuju arena boss
const BOSS_SPAWN_X = 5150;
const BOSS_ARENA_MIN_X = GATE_X + 40;
const BOSS_ARENA_MAX_X = WORLD_WIDTH - 120;

// ============================================================
// DATA LEVEL — silakan diedit untuk mengubah tata letak level
// ============================================================

// Jurang (jika tidak dilewati akan jatuh & mati).
// type 'small'  -> cukup loncat biasa
// type 'large'  -> harus loncat sambil menahan tombol Lari
const PITS = [
  { x1: 900,  x2: 990,  type: 'small' },
  { x1: 2000, x2: 2090, type: 'small' },
  { x1: 2500, x2: 2690, type: 'large' },
  { x1: 3300, x2: 3390, type: 'small' },
  { x1: 3800, x2: 3990, type: 'large' },
  { x1: 4400, x2: 4490, type: 'small' },
];

// Halangan padat yang harus diloncati (seperti peti kayu).
const OBSTACLES = [
  { x: 1300, width: 40, height: 50 },
  { x: 2200, width: 40, height: 50 },
  { x: 3500, width: 44, height: 55 },
  { x: 4700, width: 44, height: 55 },
];

// Area air: memperlambat gerakan pemain saat berada di dalamnya.
const WATER_ZONES = [
  { x1: 1420, x2: 1600 },
  { x1: 3100, x2: 3300 },
];

// Checkpoint: posisi respawn terakhir yang tercapai.
const CHECKPOINTS = [
  { x: 100 },
  { x: 1650 },
  { x: 2750 },
  { x: 4050 },
  { x: 4760 },   // tepat sebelum gerbang boss
];

// Titik spawn musuh biasa: x = posisi awal, range = jarak patroli.
const ENEMY_SPAWNS = [
  { x: 500,  range: 110 },
  { x: 1150, range: 90  },
  { x: 1800, range: 110 },
  { x: 2350, range: 90  },
  { x: 2850, range: 80  },
  { x: 3000, range: 80  },
  { x: 3650, range: 80  },
  { x: 4150, range: 90  },
  { x: 4300, range: 70  },
  { x: 4600, range: 70  },
];

function isGroundAt(x) {
  for (const p of PITS) if (x > p.x1 && x < p.x2) return false;
  return true;
}
function inWaterZone(x) {
  for (const w of WATER_ZONES) if (x > w.x1 && x < w.x2) return true;
  return false;
}

// ============================================================
// UTIL
// ============================================================
function rectsOverlap(ax, ay, aw, ah, bx, by, bw, bh) {
  return ax < bx + bw && ax + aw > bx && ay < by + bh && ay + ah > by;
}
function circleRectOverlap(cx, cy, cr, rx, ry, rw, rh) {
  const nx = Math.max(rx, Math.min(cx, rx + rw));
  const ny = Math.max(ry, Math.min(cy, ry + rh));
  const dx = cx - nx, dy = cy - ny;
  return dx * dx + dy * dy <= cr * cr;
}
function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
function rand(a, b) { return a + Math.random() * (b - a); }

// ============================================================
// INPUT
// ============================================================
const keys = {};
window.addEventListener('keydown', (e) => {
  keys[e.code] = true;
  if (gameStateName === 'playing' && (e.code === 'KeyP' || e.code === 'Escape')) {
    togglePause();
  }
  if (gameStateName === 'paused' && e.code === 'Escape') togglePause();
  if (['Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code)) e.preventDefault();
});
window.addEventListener('keyup', (e) => { keys[e.code] = false; });

function isDown(...codes) { return codes.some(c => keys[c]); }

// ============================================================
// PELURU
// ============================================================
class Bullet {
  constructor(x, y, vx, owner, opts = {}) {
    this.x = x; this.y = y; this.vx = vx;
    this.owner = owner; // 'player' | 'playerBig' | 'enemy' | 'boss'
    this.radius = opts.radius || (owner === 'playerBig' ? 11 : owner === 'player' ? 5 : 6);
    this.damage = opts.damage || (owner === 'playerBig' ? BIG_ATTACK_DAMAGE : 1);
    this.pierce = owner === 'playerBig';
    this.alive = true;
    this.trail = [];
    this.hitTargets = new Set(); // cegah 1 peluru menembus memberi damage berkali-kali ke target yang sama
  }
  update(dt) {
    this.trail.push({ x: this.x, y: this.y });
    if (this.trail.length > 5) this.trail.shift();
    this.x += this.vx * dt;
    if (this.x < -80 || this.x > WORLD_WIDTH + 80) this.alive = false;
  }
}

// ============================================================
// PEMAIN
// ============================================================
class Player {
  constructor(x, y) {
    this.spawn(x, y);
  }
  spawn(x, y) {
    this.x = x; this.y = y;
    this.vx = 0; this.vy = 0;
    this.facing = 1;
    this.state = 'idle'; // idle, walk, run, jump, attack, bigattack, hurt, dead
    this.animTime = 0;
    this.grounded = true;
    this.hits = 0;
    this.invulnTimer = 1.0;
    this.bigCharges = BIG_ATTACK_MAX;
    this.shootCooldown = 0;
    this.bigCooldown = 0;
    this.attackPoseTimer = 0;
    this.deathTimer = 0;
    this.running = false;
    this.inWater = false;
    this.alive = true;
  }
  get cx() { return this.x + PLAYER_W / 2; }
  get footY() { return this.y + PLAYER_H; }

  update(dt) {
    if (this.state === 'dead') {
      this.deathTimer += dt;
      this.animTime += dt;
      if (this.deathTimer > 1.0) respawnPlayer();
      return;
    }

    if (this.invulnTimer > 0) this.invulnTimer -= dt;
    if (this.shootCooldown > 0) this.shootCooldown -= dt;
    if (this.bigCooldown > 0) this.bigCooldown -= dt;
    if (this.attackPoseTimer > 0) this.attackPoseTimer -= dt;

    const wantLeft = isDown('ArrowLeft', 'KeyA');
    const wantRight = isDown('ArrowRight', 'KeyD');
    const wantRun = isDown('ShiftLeft', 'ShiftRight');
    const wantJump = isDown('Space', 'ArrowUp', 'KeyW');

    this.inWater = this.grounded && inWaterZone(this.cx);
    let moveDir = 0;
    if (wantLeft && !wantRight) moveDir = -1;
    else if (wantRight && !wantLeft) moveDir = 1;

    this.running = wantRun && moveDir !== 0 && this.grounded;
    let speed = this.running ? RUN_SPEED : WALK_SPEED;
    if (this.inWater) speed *= WATER_SLOW;

    // kontrol horizontal hanya saat berpijak di tanah — saat melayang,
    // kecepatan horizontal dipertahankan dari momentum saat lepas landas
    // (ini yang membuat "loncat sambil lari" mendarat lebih jauh).
    if (this.grounded) {
      if (moveDir !== 0) {
        this.vx = moveDir * speed;
        this.facing = moveDir;
      } else {
        this.vx = 0;
      }
    } else if (moveDir !== 0) {
      this.facing = moveDir; // boleh ubah arah hadap di udara, kecepatan tetap
    }

    // lompat
    if (wantJump && this.grounded) {
      this.vy = JUMP_VELOCITY;
      this.grounded = false;
      const airRunning = wantRun && moveDir !== 0;
      this.vx = this.facing * (airRunning ? RUN_SPEED : WALK_SPEED) * (this.inWater ? WATER_SLOW : 1);
    }

    // serangan normal
    if (isDown('KeyZ', 'KeyJ') && this.shootCooldown <= 0) {
      this.shootCooldown = PLAYER_SHOOT_COOLDOWN;
      this.attackPoseTimer = 0.18;
      this.lastAttackKind = 'attack';
      const bx = this.cx + this.facing * (PLAYER_W / 2 + 6);
      playerBullets.push(new Bullet(bx, this.y + 22, this.facing * BULLET_SPEED_PLAYER, 'player'));
      spawnMuzzleParticles(bx, this.y + 22);
    }
    // serangan besar
    if (isDown('KeyX', 'KeyK') && this.bigCooldown <= 0 && this.bigCharges > 0) {
      this.bigCooldown = PLAYER_BIG_COOLDOWN;
      this.bigCharges--;
      this.attackPoseTimer = 0.26;
      this.lastAttackKind = 'bigattack';
      updateBigAttackHUD();
      const bx = this.cx + this.facing * (PLAYER_W / 2 + 6);
      playerBullets.push(new Bullet(bx, this.y + 20, this.facing * (BULLET_SPEED_PLAYER + 60), 'playerBig'));
      spawnMuzzleParticles(bx, this.y + 20, '#ffb703', 10);
    }

    this.applyPhysics(dt);

    // status animasi (kecuali sudah mati barusan, misal jatuh ke jurang —
    // jangan timpa balik state 'dead' yang baru diset applyPhysics()).
    if (this.state === 'dead') {
      // biarkan; ditangani di awal update() pada frame berikutnya
    } else if (this.attackPoseTimer > 0) this.state = this.lastAttackKind || 'attack';
    else if (!this.grounded) this.state = 'jump';
    else if (moveDir !== 0 && this.running) this.state = 'run';
    else if (moveDir !== 0) this.state = 'walk';
    else this.state = 'idle';

    this.animTime += dt;
  }

  applyPhysics(dt) {
    // gerak horizontal + tabrakan halangan (kotak padat)
    let newX = this.x + this.vx * dt;
    for (const ob of OBSTACLES) {
      const topY = GROUND_Y - ob.height;
      const bodyOverlapsVertically = (this.y + PLAYER_H) > topY + 1;
      if (bodyOverlapsVertically && rectsOverlap(newX, this.y, PLAYER_W, PLAYER_H, ob.x, topY, ob.width, ob.height)) {
        if (this.vx > 0) newX = ob.x - PLAYER_W;
        else if (this.vx < 0) newX = ob.x + ob.width;
      }
    }
    // gerbang boss terkunci
    if (!gateOpen && newX + PLAYER_W > GATE_X) {
      newX = GATE_X - PLAYER_W;
      showGateMsg(true);
    } else {
      showGateMsg(false);
    }
    this.x = clamp(newX, 0, WORLD_WIDTH - PLAYER_W);

    // gravitasi
    this.vy += GRAVITY * dt;
    this.y += this.vy * dt;

    // cari permukaan penopang (tanah atau atas halangan)
    let supportY = null;
    if (isGroundAt(this.cx)) supportY = GROUND_Y;
    for (const ob of OBSTACLES) {
      const topY = GROUND_Y - ob.height;
      if (this.cx > ob.x && this.cx < ob.x + ob.width) {
        if (supportY === null || topY < supportY) supportY = topY;
      }
    }

    if (supportY !== null && this.vy >= 0 && this.footY >= supportY) {
      this.y = supportY - PLAYER_H;
      this.vy = 0;
      this.grounded = true;
    } else {
      this.grounded = false;
    }

    // jatuh ke jurang = mati
    if (this.footY > FALL_DEATH_Y) {
      triggerPlayerDeath('fall');
    }

    // checkpoint
    if (this.grounded) {
      for (const cp of CHECKPOINTS) {
        if (this.x >= cp.x && cp.x > lastCheckpointX) lastCheckpointX = cp.x;
      }
    }
  }

  takeHit() {
    if (this.invulnTimer > 0 || this.state === 'dead') return;
    this.hits++;
    this.invulnTimer = HIT_INVULN_TIME;
    updateHitIconsHUD();
    spawnMuzzleParticles(this.cx, this.y + 20, '#ff4d4d', 8);
    if (this.hits >= MAX_HITS) triggerPlayerDeath('bullet');
  }
}

function triggerPlayerDeath(reason) {
  if (player.state === 'dead') return;
  player.state = 'dead';
  player.deathTimer = 0;
  player.vx = 0; player.vy = 0;
  enemyBullets.length = 0;
  spawnMuzzleParticles(player.cx, player.y + 24, '#ffffff', 14);
}

function respawnPlayer() {
  player.spawn(lastCheckpointX + 4, GROUND_Y - PLAYER_H);
  player.hits = 0;
  player.bigCharges = BIG_ATTACK_MAX;
  updateHitIconsHUD();
  updateBigAttackHUD();
  if (boss && !boss.defeated) {
    boss.reset();
  }
}

// ============================================================
// MUSUH BIASA
// ============================================================
class Enemy {
  constructor(spawn) {
    this.homeX = spawn.x;
    this.minX = spawn.x - spawn.range;
    this.maxX = spawn.x + spawn.range;
    this.x = spawn.x;
    this.y = GROUND_Y - ENEMY_H;
    this.dir = 1;
    this.speed = 55;
    this.state = 'patrol';
    this.animTime = 0;
    this.shootCooldown = rand(0.6, 1.8);
    this.deathTimer = 0;
    this.alive = true;
    this.facing = -1;
  }
  get cx() { return this.x + ENEMY_W / 2; }

  update(dt) {
    this.animTime += dt;
    if (this.state === 'dead') {
      this.deathTimer += dt;
      return;
    }
    const distToPlayer = player.cx - this.cx;
    const seesPlayer = Math.abs(distToPlayer) < ENEMY_DETECT_RANGE && player.state !== 'dead';

    if (seesPlayer) {
      this.facing = distToPlayer > 0 ? 1 : -1;
      this.state = 'aim';
      this.shootCooldown -= dt;
      if (this.shootCooldown <= 0) {
        this.shootCooldown = rand(1.0, 1.7);
        const by = this.y + 22;
        enemyBullets.push(new Bullet(this.cx + this.facing * 20, by, this.facing * BULLET_SPEED_ENEMY, 'enemy'));
      }
    } else {
      this.state = 'patrol';
      this.x += this.dir * this.speed * dt;
      this.facing = this.dir;
      if (this.x < this.minX) { this.x = this.minX; this.dir = 1; }
      if (this.x > this.maxX) { this.x = this.maxX; this.dir = -1; }
    }
  }

  die() {
    if (this.state === 'dead') return;
    this.state = 'dead';
    this.deathTimer = 0;
    this.alive = false;
    enemiesKilled++;
    updateKillHUD();
    spawnMuzzleParticles(this.cx, this.y + 20, '#ffcf6b', 10);
    if (enemiesKilled >= ENEMIES_TO_BEAT_FOR_BOSS) gateOpen = true;
  }
}

// ============================================================
// BOSS
// ============================================================
class Boss {
  constructor() {
    this.reset();
    this.defeated = false;
  }
  reset() {
    this.x = BOSS_SPAWN_X;
    this.y = GROUND_Y - BOSS_H;
    this.hp = BOSS_HP_MAX;
    this.facing = -1;
    this.shootCooldown = 1.0;
    this.state = 'idle';
    this.animTime = 0;
    this.deathTimer = 0;
    this.defeated = false;
  }
  get cx() { return this.x + BOSS_W / 2; }

  update(dt) {
    this.animTime += dt;
    if (this.state === 'dead') {
      this.deathTimer += dt;
      if (this.deathTimer > 1.4 && !this.defeated) {
        this.defeated = true;
        onBossDefeated();
      }
      return;
    }
    const dist = player.cx - this.cx;
    this.facing = dist > 0 ? 1 : -1;

    let moveSpeed = 0;
    if (Math.abs(dist) > 260) moveSpeed = this.facing * 95;
    else if (Math.abs(dist) < 130) moveSpeed = -this.facing * 70;
    this.x = clamp(this.x + moveSpeed * dt, BOSS_ARENA_MIN_X, BOSS_ARENA_MAX_X);
    this.state = moveSpeed !== 0 ? 'walk' : 'idle';

    this.shootCooldown -= dt;
    if (this.shootCooldown <= 0 && player.state !== 'dead') {
      this.shootCooldown = rand(0.7, 1.0);
      const by = this.y + 34;
      enemyBullets.push(new Bullet(this.cx + this.facing * 30, by, this.facing * BULLET_SPEED_BOSS, 'boss', { damage: BOSS_BULLET_DAMAGE }));
    }
  }

  hit(damage) {
    if (this.state === 'dead') return;
    this.hp -= damage;
    updateBossHUD();
    spawnMuzzleParticles(this.cx, this.y + 30, '#ffcf6b', 6);
    if (this.hp <= 0) {
      this.hp = 0;
      this.state = 'dead';
      this.deathTimer = 0;
      updateBossHUD();
    }
  }
}

function onBossDefeated() {
  gameStateName = 'ending';
  showScreen('screenEnding');
}

// ============================================================
// PARTIKEL (efek visual ringan)
// ============================================================
const particles = [];
function spawnMuzzleParticles(x, y, color = '#fff2c2', count = 5) {
  for (let i = 0; i < count; i++) {
    particles.push({
      x, y,
      vx: rand(-140, 140), vy: rand(-160, -20),
      life: rand(0.25, 0.5), maxLife: 0.5, color,
    });
  }
}
function updateParticles(dt) {
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.life -= dt;
    if (p.life <= 0) { particles.splice(i, 1); continue; }
    p.x += p.vx * dt; p.y += p.vy * dt;
    p.vy += 500 * dt;
  }
}

// ============================================================
// STATE GLOBAL GAME
// ============================================================
let gameStateName = 'menu'; // menu, howto, intro, playing, paused, ending
let player = new Player(80, GROUND_Y - PLAYER_H);
let enemies = [];
let boss = null;
let playerBullets = [];
let enemyBullets = [];
let enemiesKilled = 0;
let gateOpen = false;
let lastCheckpointX = CHECKPOINTS[0].x;
let cameraX = 0;
let worldTime = 0;

function initGame() {
  player = new Player(80, GROUND_Y - PLAYER_H);
  enemies = ENEMY_SPAWNS.map(s => new Enemy(s));
  boss = null;
  playerBullets = [];
  enemyBullets = [];
  particles.length = 0;
  enemiesKilled = 0;
  gateOpen = false;
  lastCheckpointX = CHECKPOINTS[0].x;
  cameraX = 0;
  updateHitIconsHUD();
  updateBigAttackHUD();
  updateKillHUD();
  document.getElementById('bossBarWrap').style.display = 'none';
  showGateMsg(false);
}

// ============================================================
// UPDATE UTAMA
// ============================================================
function updateGame(dt) {
  worldTime += dt;
  player.update(dt);

  for (const e of enemies) e.update(dt);

  if (!boss && gateOpen && player.cx > GATE_X) {
    boss = new Boss();
    document.getElementById('bossBarWrap').style.display = 'block';
    updateBossHUD();
  }
  if (boss) boss.update(dt);

  // peluru pemain
  for (let i = playerBullets.length - 1; i >= 0; i--) {
    const b = playerBullets[i];
    b.update(dt);
    if (!b.alive) { playerBullets.splice(i, 1); continue; }
    let hitSomething = false;
    for (const e of enemies) {
      if (e.state === 'dead' || b.hitTargets.has(e)) continue;
      if (circleRectOverlap(b.x, b.y, b.radius, e.x, e.y, ENEMY_W, ENEMY_H)) {
        e.die();
        b.hitTargets.add(e);
        hitSomething = true;
        if (!b.pierce) break;
      }
    }
    if (boss && boss.state !== 'dead' && !b.hitTargets.has(boss) &&
        circleRectOverlap(b.x, b.y, b.radius, boss.x, boss.y, BOSS_W, BOSS_H)) {
      boss.hit(b.damage);
      b.hitTargets.add(boss);
      hitSomething = true;
    }
    if (hitSomething && !b.pierce) { b.alive = false; playerBullets.splice(i, 1); }
  }

  // peluru musuh
  for (let i = enemyBullets.length - 1; i >= 0; i--) {
    const b = enemyBullets[i];
    b.update(dt);
    if (!b.alive) { enemyBullets.splice(i, 1); continue; }
    if (player.state !== 'dead' && circleRectOverlap(b.x, b.y, b.radius, player.x, player.y, PLAYER_W, PLAYER_H)) {
      player.takeHit();
      enemyBullets.splice(i, 1);
    }
  }

  updateParticles(dt);

  // kamera mengikuti pemain
  const targetCam = clamp(player.cx - CANVAS_W / 2, 0, WORLD_WIDTH - CANVAS_W);
  cameraX += (targetCam - cameraX) * Math.min(1, dt * 6);
}

// ============================================================
// RENDER LATAR & LEVEL
// ============================================================
const ctx = document.getElementById('game').getContext('2d');

function drawBackground() {
  const g = ctx.createLinearGradient(0, 0, 0, CANVAS_H);
  g.addColorStop(0, '#7ec8e3');
  g.addColorStop(0.55, '#bfe3f0');
  g.addColorStop(1, '#e8f6ef');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

  // matahari
  ctx.fillStyle = 'rgba(255,247,214,0.9)';
  ctx.beginPath(); ctx.arc(120 - cameraX * 0.05, 90, 46, 0, Math.PI * 2); ctx.fill();

  // bukit jauh (paralaks)
  drawHillLayer(cameraX * 0.25, 300, 90, 'rgba(120,150,110,0.55)');
  drawHillLayer(cameraX * 0.45, 335, 70, 'rgba(90,125,90,0.65)');
}
function drawHillLayer(offset, baseY, amp, color) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(0, CANVAS_H);
  const period = 400;
  for (let x = -period; x <= CANVAS_W + period; x += 40) {
    const worldX = x + offset;
    const y = baseY - Math.sin(worldX / period * Math.PI * 2) * amp * 0.4 - amp * 0.3;
    ctx.lineTo(x, y);
  }
  ctx.lineTo(CANVAS_W, CANVAS_H);
  ctx.closePath();
  ctx.fill();
}

function drawGround() {
  const viewX1 = cameraX - 20, viewX2 = cameraX + CANVAS_W + 20;
  // gabungkan segmen padat di antara jurang
  const sorted = [...PITS].sort((a, b) => a.x1 - b.x1);
  let cursor = 0;
  const segments = [];
  for (const p of sorted) {
    if (p.x1 > cursor) segments.push({ x1: cursor, x2: p.x1 });
    cursor = p.x2;
  }
  segments.push({ x1: cursor, x2: WORLD_WIDTH });

  for (const seg of segments) {
    if (seg.x2 < viewX1 || seg.x1 > viewX2) continue;
    const sx1 = seg.x1 - cameraX, sx2 = seg.x2 - cameraX;
    ctx.fillStyle = '#8a5a35';
    ctx.fillRect(sx1, GROUND_Y, sx2 - sx1, CANVAS_H - GROUND_Y);
    ctx.fillStyle = '#4caf6b';
    ctx.fillRect(sx1, GROUND_Y, sx2 - sx1, 10);
    ctx.fillStyle = '#3f8f57';
    for (let gx = seg.x1; gx < seg.x2; gx += 18) {
      ctx.fillRect(gx - cameraX, GROUND_Y - 4, 4, 8);
    }
  }

  // jurang (void gelap)
  for (const p of sorted) {
    if (p.x2 < viewX1 || p.x1 > viewX2) continue;
    const sx1 = p.x1 - cameraX, sx2 = p.x2 - cameraX;
    const g = ctx.createLinearGradient(0, GROUND_Y, 0, CANVAS_H);
    g.addColorStop(0, '#241b16');
    g.addColorStop(1, '#000000');
    ctx.fillStyle = g;
    ctx.fillRect(sx1, GROUND_Y, sx2 - sx1, CANVAS_H - GROUND_Y);
    if (p.type === 'large') {
      ctx.fillStyle = 'rgba(230,57,70,0.65)';
      ctx.font = '11px Consolas, monospace';
      ctx.textAlign = 'center';
      ctx.fillText('LONCAT + LARI', (sx1 + sx2) / 2, GROUND_Y - 10);
    }
  }
}

function drawWater() {
  for (const w of WATER_ZONES) {
    if (w.x2 < cameraX || w.x1 > cameraX + CANVAS_W) continue;
    const sx1 = w.x1 - cameraX, sx2 = w.x2 - cameraX;
    ctx.fillStyle = 'rgba(45,140,200,0.55)';
    ctx.fillRect(sx1, GROUND_Y + 2, sx2 - sx1, 14);
    ctx.strokeStyle = 'rgba(255,255,255,0.5)';
    ctx.lineWidth = 1.5;
    for (let i = 0; i < 4; i++) {
      const wy = GROUND_Y + 5 + i * 3;
      ctx.beginPath();
      for (let x = sx1; x <= sx2; x += 8) {
        const yy = wy + Math.sin((x + worldTime * 90 + i * 20) / 14) * 1.5;
        if (x === sx1) ctx.moveTo(x, yy); else ctx.lineTo(x, yy);
      }
      ctx.stroke();
    }
  }
}

function drawObstacles() {
  for (const ob of OBSTACLES) {
    const sx = ob.x - cameraX;
    if (sx < -60 || sx > CANVAS_W + 60) continue;
    const topY = GROUND_Y - ob.height;
    ctx.fillStyle = '#8a5a2b';
    ctx.fillRect(sx, topY, ob.width, ob.height);
    ctx.strokeStyle = '#5c3a19';
    ctx.lineWidth = 2;
    ctx.strokeRect(sx + 1, topY + 1, ob.width - 2, ob.height - 2);
    ctx.beginPath();
    ctx.moveTo(sx, topY); ctx.lineTo(sx + ob.width, topY + ob.height);
    ctx.moveTo(sx + ob.width, topY); ctx.lineTo(sx, topY + ob.height);
    ctx.stroke();
  }
}

function drawCheckpoints() {
  for (const cp of CHECKPOINTS) {
    const sx = cp.x - cameraX;
    if (sx < -30 || sx > CANVAS_W + 30) continue;
    const reached = cp.x <= lastCheckpointX;
    ctx.strokeStyle = '#555';
    ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(sx, GROUND_Y); ctx.lineTo(sx, GROUND_Y - 46); ctx.stroke();
    ctx.fillStyle = reached ? '#3ddc6f' : '#888';
    ctx.beginPath();
    ctx.moveTo(sx, GROUND_Y - 46);
    ctx.lineTo(sx + 20, GROUND_Y - 38);
    ctx.lineTo(sx, GROUND_Y - 30);
    ctx.closePath();
    ctx.fill();
  }
}

function drawGate() {
  const sx = GATE_X - cameraX;
  if (sx < -40 || sx > CANVAS_W + 40) return;
  if (gateOpen) return;
  const pulse = 0.5 + 0.5 * Math.sin(worldTime * 6);
  ctx.fillStyle = `rgba(230,57,70,${0.35 + pulse * 0.25})`;
  ctx.fillRect(sx - 6, GROUND_Y - 140, 12, 140);
  ctx.fillStyle = '#ffb703';
  ctx.font = 'bold 13px Consolas, monospace';
  ctx.textAlign = 'center';
  ctx.fillText(`${Math.max(0, ENEMIES_TO_BEAT_FOR_BOSS - enemiesKilled)} MUSUH LAGI`, sx, GROUND_Y - 150);
}

// ---------------- SPRITE HUMANOID (pemain / musuh / boss) ----------------
function drawHumanoid(px, py, facing, palette, pose) {
  // px,py = titik kaki (bottom-center) di layar
  const s = pose.scale || 1;
  ctx.save();
  ctx.translate(px, py);
  ctx.scale(facing * s, s);
  ctx.globalAlpha = pose.alpha != null ? pose.alpha : 1;

  if (pose.collapsed) {
    ctx.rotate(Math.PI / 2 * Math.min(1, pose.collapseT));
    ctx.translate(0, -8);
  }

  const legLen = pose.legLen, torsoH = pose.torsoH, headR = pose.headR, armLen = pose.armLen;
  const hipY = -legLen;
  const shoulderY = hipY - torsoH;

  // kaki belakang
  ctx.save();
  ctx.translate(0, hipY);
  ctx.rotate(-pose.legAngle);
  ctx.fillStyle = palette.dark;
  ctx.fillRect(-3, 0, 6, legLen);
  ctx.restore();

  // kaki depan
  ctx.save();
  ctx.translate(0, hipY);
  ctx.rotate(pose.legAngle);
  ctx.fillStyle = palette.main;
  ctx.fillRect(-3, 0, 6, legLen);
  ctx.restore();

  // torso
  ctx.fillStyle = palette.main;
  ctx.fillRect(-8, shoulderY, 16, torsoH);

  // lengan belakang
  ctx.save();
  ctx.translate(0, shoulderY + 4);
  ctx.rotate(-pose.armAngle);
  ctx.fillStyle = palette.dark;
  ctx.fillRect(-3, 0, 6, armLen);
  ctx.restore();

  // kepala
  ctx.fillStyle = palette.skin;
  ctx.beginPath(); ctx.arc(0, shoulderY - headR + 2, headR, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = palette.helmet;
  ctx.beginPath(); ctx.arc(0, shoulderY - headR + 2, headR, Math.PI, 0); ctx.fill();

  // lengan depan (senjata saat menyerang)
  ctx.save();
  ctx.translate(0, shoulderY + 4);
  ctx.rotate(pose.armFrontAngle);
  ctx.fillStyle = palette.main;
  ctx.fillRect(-3, 0, 6, armLen);
  if (pose.weapon) {
    ctx.fillStyle = pose.weaponColor || '#333';
    ctx.fillRect(armLen - 4, -3, pose.weaponBig ? 20 : 14, 6);
  }
  ctx.restore();

  ctx.restore();
}

function poseFor(state, animTime, opts = {}) {
  const pose = {
    scale: opts.scale || 1,
    legLen: opts.legLen || 26,
    torsoH: opts.torsoH || 22,
    headR: opts.headR || 9,
    armLen: opts.armLen || 20,
    legAngle: 0, armAngle: 0, armFrontAngle: 0,
    alpha: 1, collapsed: false, collapseT: 0,
    weapon: false, weaponBig: false,
  };
  const walkCycle = Math.sin(animTime * 9);
  const runCycle = Math.sin(animTime * 15);

  switch (state) {
    case 'walk':
      pose.legAngle = walkCycle * 0.5;
      pose.armAngle = -walkCycle * 0.4;
      pose.armFrontAngle = walkCycle * 0.4;
      break;
    case 'run':
      pose.legAngle = runCycle * 0.75;
      pose.armAngle = -runCycle * 0.6;
      pose.armFrontAngle = runCycle * 0.6;
      break;
    case 'jump':
      pose.legAngle = -0.35;
      pose.armAngle = -0.6;
      pose.armFrontAngle = -0.9;
      break;
    case 'attack':
      pose.legAngle = 0.05;
      pose.armFrontAngle = -1.15;
      pose.weapon = true;
      break;
    case 'bigattack':
      pose.legAngle = 0.1;
      pose.armFrontAngle = -1.3;
      pose.weapon = true;
      pose.weaponBig = true;
      break;
    case 'aim':
      pose.armFrontAngle = -1.0;
      pose.weapon = true;
      break;
    case 'dead':
      pose.collapsed = true;
      pose.collapseT = Math.min(1, animTime * 2.2);
      pose.alpha = Math.max(0.35, 1 - animTime * 0.4);
      break;
    default: // idle
      pose.legAngle = 0;
      pose.armAngle = Math.sin(animTime * 2) * 0.05;
      break;
  }
  return pose;
}

const PLAYER_PALETTE = { main: '#2e5c8a', dark: '#1f3864', skin: '#e8b98a', helmet: '#274b6b' };
const ENEMY_PALETTE  = { main: '#7a2b2b', dark: '#521c1c', skin: '#d9a97a', helmet: '#3a1414' };
const BOSS_PALETTE   = { main: '#4a1f5c', dark: '#301040', skin: '#caa3d9', helmet: '#1f0a2b' };

function drawPlayer() {
  const timeParam = player.state === 'dead' ? player.deathTimer : player.animTime;
  const pose = poseFor(player.state, timeParam, { legLen: 27, torsoH: 24, headR: 9, armLen: 21 });
  if (player.invulnTimer > 0 && player.state !== 'dead') {
    pose.alpha = (Math.floor(worldTime * 14) % 2 === 0) ? 0.4 : 1;
  }
  drawHumanoid(player.x + PLAYER_W / 2 - cameraX, player.footY, player.facing, PLAYER_PALETTE, pose);
}

function drawEnemies() {
  for (const e of enemies) {
    const sx = e.x + ENEMY_W / 2 - cameraX;
    if (sx < -40 || sx > CANVAS_W + 40) continue;
    const st = e.state === 'dead' ? 'dead' : e.state;
    const timeParam = st === 'dead' ? e.deathTimer : e.animTime;
    const pose = poseFor(st === 'patrol' ? 'walk' : st, timeParam, { legLen: 25, torsoH: 22, headR: 8, armLen: 19 });
    drawHumanoid(sx, GROUND_Y, e.facing, ENEMY_PALETTE, pose);
  }
}

function drawBoss() {
  if (!boss) return;
  const sx = boss.cx - cameraX;
  const timeParam = boss.state === 'dead' ? boss.deathTimer : boss.animTime;
  const pose = poseFor(boss.state, timeParam, { scale: 1.7, legLen: 27, torsoH: 26, headR: 11, armLen: 22 });
  drawHumanoid(sx, GROUND_Y, boss.facing, BOSS_PALETTE, pose);
}

function drawBullets() {
  for (const b of playerBullets) {
    ctx.fillStyle = b.owner === 'playerBig' ? '#ffb703' : '#7fd7ff';
    ctx.beginPath(); ctx.arc(b.x - cameraX, b.y, b.radius, 0, Math.PI * 2); ctx.fill();
  }
  for (const b of enemyBullets) {
    ctx.fillStyle = b.owner === 'boss' ? '#ff8a3d' : '#ff4d4d';
    ctx.beginPath(); ctx.arc(b.x - cameraX, b.y, b.radius, 0, Math.PI * 2); ctx.fill();
  }
}

function drawParticles() {
  for (const p of particles) {
    ctx.globalAlpha = Math.max(0, p.life / p.maxLife);
    ctx.fillStyle = p.color;
    ctx.fillRect(p.x - cameraX - 2, p.y - 2, 4, 4);
  }
  ctx.globalAlpha = 1;
}

function drawDeathMessage() {
  if (player.state !== 'dead') return;
  ctx.fillStyle = 'rgba(0,0,0,0.35)';
  ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
  ctx.fillStyle = '#ff5c5c';
  ctx.font = 'bold 28px Consolas, monospace';
  ctx.textAlign = 'center';
  ctx.fillText('KAMU MATI', CANVAS_W / 2, CANVAS_H / 2 - 10);
  ctx.fillStyle = '#ddd';
  ctx.font = '14px Consolas, monospace';
  ctx.fillText('Melanjutkan dari checkpoint...', CANVAS_W / 2, CANVAS_H / 2 + 16);
}

function renderGame() {
  drawBackground();
  drawGround();
  drawWater();
  drawObstacles();
  drawCheckpoints();
  drawGate();
  drawEnemies();
  drawBoss();
  drawPlayer();
  drawBullets();
  drawParticles();
  drawDeathMessage();
}

// ============================================================
// HUD
// ============================================================
function updateHitIconsHUD() {
  const wrap = document.getElementById('hitIcons');
  wrap.innerHTML = '';
  for (let i = 0; i < MAX_HITS; i++) {
    const d = document.createElement('div');
    d.className = 'hit-icon' + (i < player.hits ? ' used' : '');
    wrap.appendChild(d);
  }
}
function updateBigAttackHUD() {
  document.getElementById('bigAttackCounter').textContent = `Serangan Besar: ${player.bigCharges}`;
}
function updateKillHUD() {
  document.getElementById('killCounter').textContent = `Musuh Dikalahkan: ${enemiesKilled} / ${ENEMIES_TO_BEAT_FOR_BOSS}`;
}
function updateBossHUD() {
  if (!boss) return;
  const pct = Math.max(0, boss.hp / BOSS_HP_MAX) * 100;
  document.getElementById('bossBar').style.width = pct + '%';
}
function showGateMsg(show) {
  document.getElementById('gateMsg').style.display = show ? 'block' : 'none';
}

// ============================================================
// MANAJEMEN LAYAR (menu / cerita / main)
// ============================================================
const screens = ['screenMenu', 'screenHowTo', 'screenIntro', 'screenEnding', 'screenGame'];
function showScreen(id) {
  for (const s of screens) document.getElementById(s).classList.toggle('hidden', s !== id);
}

function applyStoryData() {
  document.getElementById('pageTitle').textContent = STORY_DATA.menu.title;
  document.getElementById('menuTitle').textContent = STORY_DATA.menu.title;
  document.getElementById('menuSubtitle').textContent = STORY_DATA.menu.subtitle;

  document.getElementById('introTitle').textContent = STORY_DATA.intro.title;
  document.getElementById('introImage').src = STORY_DATA.intro.image;
  document.getElementById('introText').textContent = STORY_DATA.intro.text;

  document.getElementById('endingTitle').textContent = STORY_DATA.ending.title;
  document.getElementById('endingImage').src = STORY_DATA.ending.image;
  document.getElementById('endingText').textContent = STORY_DATA.ending.text;
}

function togglePause() {
  if (gameStateName === 'playing') {
    gameStateName = 'paused';
    document.getElementById('pauseOverlay').classList.add('show');
  } else if (gameStateName === 'paused') {
    gameStateName = 'playing';
    document.getElementById('pauseOverlay').classList.remove('show');
  }
}

document.getElementById('btnStart').addEventListener('click', () => {
  gameStateName = 'intro';
  showScreen('screenIntro');
});
document.getElementById('btnHowTo').addEventListener('click', () => {
  gameStateName = 'howto';
  showScreen('screenHowTo');
});
document.getElementById('btnBackMenu').addEventListener('click', () => {
  gameStateName = 'menu';
  showScreen('screenMenu');
});
document.getElementById('btnIntroContinue').addEventListener('click', () => {
  initGame();
  gameStateName = 'playing';
  showScreen('screenGame');
});
document.getElementById('btnEndingMenu').addEventListener('click', () => {
  gameStateName = 'menu';
  showScreen('screenMenu');
});
document.getElementById('btnResume').addEventListener('click', togglePause);
document.getElementById('btnQuitMenu').addEventListener('click', () => {
  document.getElementById('pauseOverlay').classList.remove('show');
  gameStateName = 'menu';
  showScreen('screenMenu');
});

// ============================================================
// LOOP UTAMA
// ============================================================
let lastTime = performance.now();
function loop(now) {
  let dt = (now - lastTime) / 1000;
  lastTime = now;
  dt = Math.min(dt, 1 / 30); // hindari lompatan besar saat tab tidak aktif

  if (gameStateName === 'playing') {
    updateGame(dt);
    renderGame();
  }
  requestAnimationFrame(loop);
}

applyStoryData();
showScreen('screenMenu');
requestAnimationFrame(loop);
