# Petualangan Eldoria — Turn-Based RPG (Pygame)

Game RPG turn-based sederhana dengan sistem level, naik stat, dan 10 Boss.
Progres otomatis tersimpan (save/load) di `saves/save1.json`.

## Menjalankan game

```bash
pip install pygame
python main.py
```

## Cara bermain

- Setiap level, kalahkan 2 musuh biasa lebih dulu, lalu hadapi Boss level tersebut.
- Setelah mengalahkan Boss, kamu naik level dan boleh memilih menaikkan salah satu:
  **Health Point**, **Offense (attack)**, atau **Defense**.
- Level maksimal adalah 10. Boss level 10 adalah Boss terakhir (Penguasa Kegelapan).
- Saat bertarung, gunakan tombol **Serang** untuk menyerang atau **Bertahan** untuk
  mengurangi separuh damage yang masuk di giliran itu — bertahan sesekali sangat
  membantu melawan Boss.
- Jika kalah, HP akan dipulihkan penuh dan kamu bisa mencoba lagi dari level yang sama
  (tekan ENTER di layar Game Over).

## Cara mengganti gambar tokoh, musuh, dan Boss (TANPA mengubah kode)

Semua gambar ada di folder `assets/images/`:

- `assets/images/player.png` — gambar tokoh utama.
- `assets/images/enemies/enemy1.png` s.d. `enemy10.png` — 10 musuh biasa.
- `assets/images/bosses/boss1.png` s.d. `boss10.png` — 10 Boss (boss1 = level 1, ...,
  boss10 = level 10).

Cukup **ganti file PNG** dengan gambar barumu memakai **nama file yang sama**, ukuran
berapa pun juga tidak masalah karena akan otomatis di-scale oleh game. Kalau ingin
memakai nama file lain, ubah juga path `"image"` di file JSON terkait (lihat di bawah).

Jika sebuah file gambar belum ada/hilang, game tidak akan crash — ia akan menampilkan
kotak abu-abu berlabel nama filenya sebagai placeholder.

## Cara mengganti teks/cerita dan statistik (TANPA mengubah kode)

Semua teks dan angka game ada di folder `data/`, dalam format JSON yang mudah diedit:

- `data/story.json`
  - `"intro"`: daftar kalimat pembuka cerita (tampil satu per satu di awal game).
  - `"level_up"`: teks yang muncul di layar naik level.
  - `"boss_intro"`: teks pembuka saat bertemu tiap Boss, key-nya adalah nomor level ("1".."10").
  - `"ending"`: teks penutup saat Boss level 10 dikalahkan.

- `data/characters.json`
  - Statistik awal tokoh utama (`base_hp`, `base_attack`, `base_defense`) dan besar
    kenaikan stat tiap kali naik level (`hp_per_point`, `attack_per_point`,
    `defense_per_point`).

- `data/enemies.json`
  - Daftar musuh biasa. Tiap entri punya `name`, `image`, `hp`, `attack`, `defense`,
    serta `min_level`/`max_level` yang menentukan di level berapa musuh ini bisa muncul.

- `data/bosses.json`
  - Daftar 10 Boss. Tiap entri terikat pada satu `level` (1–10) dengan `name`,
    `image`, `hp`, `attack`, `defense`.

Setelah mengedit file-file di atas, cukup jalankan ulang `python main.py` — tidak perlu
mengubah kode Python sama sekali.

## Struktur folder

```
python/
  main.py                 -> game loop utama & semua layar (menu, cerita, battle, dll)
  game/
    constants.py           -> pengaturan layar, warna, MAX_LEVEL, dsb.
    data_loader.py          -> pemuat data dari folder data/
    save_system.py          -> baca/tulis file save JSON
    combat.py                -> logika pertarungan (damage, HP, dsb.)
    ui.py                     -> helper gambar, teks, tombol
  data/
    characters.json           -> stat tokoh utama
    enemies.json               -> daftar musuh biasa
    bosses.json                 -> daftar 10 boss
    story.json                   -> semua teks cerita
  assets/images/                 -> semua gambar (lihat bagian di atas)
  saves/save1.json                -> file save otomatis (dibuat saat pertama main)
```

## Menyeimbangkan tingkat kesulitan

Jika game terasa terlalu mudah/sulit, cukup ubah angka `hp`, `attack`, `defense` di
`data/bosses.json` / `data/enemies.json`, atau ubah `hp_per_point` / `attack_per_point`
/ `defense_per_point` di `data/characters.json`. Tidak perlu menyentuh kode Python.
