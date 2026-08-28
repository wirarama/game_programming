# Simple FPS (Pygame Raycaster) — Menu, Cerita, dan Bisa Dipastikan Tamat

Kontrol:
- `W/A/S/D` : gerak
- Mouse : lihat kiri/kanan (saat sedang bermain)
- Panah Kiri/Kanan : alternatif menoleh tanpa mouse
- Klik kiri : tembak (saat bermain) / pilih tombol (di menu & layar cerita)
- `ENTER` / klik : lanjut di layar cerita
- `ESC` : keluar

## Alur permainan

1. **Menu utama** — gambar latar + tombol Mulai & Keluar (semuanya gambar, bisa diedit).
2. **Cerita awal** — gambar + teks pembuka sebelum pertempuran dimulai.
3. Habiskan semua **musuh biasa** (jumlah & statistik diatur di `data/config.json`).
4. **Cerita sebelum Boss** — muncul begitu semua musuh biasa habis, sebelum Boss benar-benar muncul.
5. Kalahkan **Boss** yang jauh lebih kuat.
6. **Cerita kemenangan (ending)** — gambar + teks setelah Boss dikalahkan.

### Kalau kamu mati

Game **tidak langsung berakhir**. Muncul layar dengan tombol **Lanjutkan** dan
**Keluar**. Pilih Lanjutkan untuk hidup lagi dengan HP penuh dan melanjutkan
dari posisi terakhir — musuh yang sudah kamu lukai/kalahkan tetap seperti itu,
Boss yang sudah muncul juga tetap ada. Dengan begini, siapapun cepat atau
lambat pasti bisa menyelesaikan game ini.

## Mengedit game lewat `data/config.json` (tanpa sentuh kode Python)

### Menu & layar cerita (gambar + teks)

- `ui.main_menu.background` / `.title` / `.subtitle` — latar & judul menu utama.
- `ui.main_menu.start_button` / `.quit_button` — gambar tombol Mulai & Keluar di menu.
- `ui.continue_screen.background` / `.title` / `.message` — latar, judul, pesan saat kamu mati.
- `ui.continue_screen.continue_button` / `.quit_button` — gambar tombol Lanjutkan & Keluar.
- `story.intro.image` / `.title` / `.text` — cerita awal permainan.
- `story.before_boss.image` / `.title` / `.text` — cerita sebelum Boss muncul.
- `story.ending.image` / `.title` / `.text` — cerita setelah Boss dikalahkan.

### Jumlah tembakan/serangan yang menyebabkan mati (`combat`)

HP musuh, HP Boss, dan damage serangan musuh/Boss **dihitung otomatis** dari
angka-angka ini — kamu tidak perlu mengatur HP secara manual:

- `combat.player_hp` — HP pemain.
- `combat.player_shoot_damage` — damage tiap kali kamu menembak.
- `combat.player_shoot_cooldown` — jeda antar tembakan (dalam frame).
- `combat.shots_to_kill_enemy` — **berapa kali tembak sampai 1 musuh biasa mati**.
- `combat.shots_to_kill_boss` — **berapa kali tembak sampai Boss mati**.
- `combat.enemy_hits_to_kill_player` — **berapa kali kena serang musuh biasa sampai kamu mati**.
- `combat.boss_hits_to_kill_player` — **berapa kali kena serang Boss sampai kamu mati**.
- `combat.enemy_attack_interval` / `combat.boss_attack_interval` — jeda antar serangan musuh/Boss (detik).

### Statistik lain

- `player.move_speed` — kecepatan gerak pemain (unit/detik).
- `enemy.count` — jumlah musuh biasa yang muncul di awal.
- `enemy.speed` / `enemy.image` — kecepatan gerak & gambar musuh biasa.
- `boss.speed` / `boss.image` / `boss.name` — kecepatan gerak, gambar, & nama Boss.
- `boss.spawn_message` — teks yang tampil sesaat saat Boss pertama kali muncul.

## Mengganti gambar

Cukup timpa file di `assets/images/` dengan nama file yang sama (atau ubah
path-nya di `data/config.json`):

- `assets/images/enemy.png` — tampilan musuh biasa.
- `assets/images/boss.png` — tampilan Boss.
- `assets/images/ui/menu_background.png` — latar belakang menu utama & layar "lanjutkan".
- `assets/images/ui/button_start.png` — tombol Mulai.
- `assets/images/ui/button_quit.png` — tombol Keluar.
- `assets/images/ui/button_continue.png` — tombol Lanjutkan.
- `assets/images/story/intro.png` — gambar cerita awal.
- `assets/images/story/before_boss.png` — gambar cerita sebelum Boss.
- `assets/images/story/ending.png` — gambar cerita kemenangan.

Ukuran gambar bebas, akan otomatis di-scale oleh game. Kalau file belum ada,
game tetap berjalan memakai kotak placeholder berwarna berlabel nama.

## Struktur folder

```
fps_game/
  main.py                    -> semua logika game (menu, cerita, raycasting, musuh, boss)
  data/config.json             -> semua pengaturan (menu, cerita, combat, statistik, path gambar)
  assets/images/
    enemy.png, boss.png          -> tampilan musuh & boss
    ui/                            -> background & tombol menu/layar lanjutkan
    story/                          -> gambar cerita awal, sebelum boss, ending
```
