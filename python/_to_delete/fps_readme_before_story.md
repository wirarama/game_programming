# Simple FPS (Pygame Raycaster) — HP Besar, Musuh & Boss Bisa Diedit

Kontrol:
- `W/A/S/D` : gerak
- Mouse : lihat kiri/kanan
- Klik kiri : tembak
- `ESC` : keluar

## Alur permainan

1. Habiskan semua musuh biasa (jumlah & statistik diatur di `data/config.json`).
2. Setelah musuh biasa habis, **Boss** yang jauh lebih kuat akan muncul otomatis.
3. Kalahkan Boss untuk memenangkan game dan melihat layar ending (gambar + teks).
4. HP pemain sengaja dibuat jauh lebih besar daripada HP musuh biasa maupun Boss
   supaya tidak cepat mati.

## Mengedit game lewat `data/config.json` (tanpa sentuh kode Python)

- `player.hp` — HP pemain (defaultnya jauh lebih besar dari HP musuh).
- `player.move_speed`, `player.shoot_damage`, `player.shoot_cooldown`.
- `enemy.count` — jumlah musuh biasa yang muncul di awal.
- `enemy.hp`, `enemy.speed`, `enemy.contact_damage_per_frame` — statistik musuh biasa.
- `enemy.image` — path gambar musuh biasa.
- `boss.hp`, `boss.speed`, `boss.contact_damage_per_frame`, `boss.name` — statistik Boss.
- `boss.image` — path gambar Boss.
- `boss.spawn_message` — teks yang tampil sesaat saat Boss pertama kali muncul.
- `ending.image` — gambar yang tampil di layar kemenangan.
- `ending.title`, `ending.text` — judul & isi teks layar kemenangan.

## Mengganti gambar

Cukup timpa file di `assets/images/`:
- `assets/images/enemy.png` — tampilan musuh biasa.
- `assets/images/boss.png` — tampilan Boss.
- `assets/images/ending.png` — gambar di layar ending/kemenangan.

Ukuran gambar bebas, akan otomatis di-scale oleh game. Kalau file belum ada,
game tetap berjalan memakai kotak placeholder berwarna berlabel nama.

## Struktur folder

```
fps_game/
  main.py               -> semua logika game (raycasting, musuh, boss, ending)
  data/config.json        -> semua pengaturan (HP, statistik, path gambar, teks ending)
  assets/images/            -> enemy.png, boss.png, ending.png
```
