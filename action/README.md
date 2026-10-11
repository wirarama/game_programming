# Garda Perbatasan — Game 2D Action

Game aksi 2D berbasis HTML5 Canvas (murni JavaScript, tanpa build tool,
tanpa library luar). Langsung jalan dengan membuka `index.html` di browser.

## Cara menjalankan

Klik dua kali `index.html`, atau buka lewat browser (Chrome/Edge/Firefox).
Tidak perlu server maupun instalasi apa pun.

> Jika ingin menjalankan lewat server lokal (opsional, misalnya lewat
> ekstensi "Live Server"), itu juga tetap berfungsi — game tidak
> memerlukan koneksi internet maupun `fetch`.

## Kontrol

| Tombol | Aksi |
|---|---|
| `←` / `→` atau `A` / `D` | Jalan |
| Tahan `Shift` sambil jalan | Lari |
| `Spasi` | Loncat (loncat sambil menahan **Lari** = loncat lebih jauh, untuk melewati jurang lebar) |
| `Z` (atau `J`) | Serangan (tembak) |
| `X` (atau `K`) | Serangan Besar — hanya bisa dipakai **2 kali**, terisi ulang saat pemain mati |
| `P` / `Esc` | Jeda |

## Fitur yang sudah diimplementasikan

- Aksi jalan, lari, menyerang (tembak), dan loncat, masing-masing dengan animasi sendiri
  (idle, jalan, lari, loncat, menyerang, serangan besar, dan mati) — semua digambar langsung
  lewat Canvas API (tidak perlu file gambar sprite).
- Musuh yang menembakkan peluru ke arah pemain dan mati jika kena 1x tembakan pemain.
- Jurang (`PITS`): jurang kecil cukup dilewati dengan loncatan biasa, jurang besar hanya bisa
  dilewati dengan loncat sambil menahan tombol Lari (loncatan jauh). Jatuh ke jurang = mati.
- Halangan padat (`OBSTACLES`) yang harus diloncati.
- Area air (`WATER_ZONES`) yang memperlambat gerakan pemain selama berada di dalamnya.
- Pemain mati jika terkena **3 peluru** musuh.
- Setelah **10 musuh** dikalahkan, gerbang menuju arena Boss terbuka dan Boss otomatis muncul
  saat pemain memasuki arena.
- Halaman Menu, Cerita Awal, dan Cerita Akhir — teks dan gambarnya bisa diedit bebas lewat
  `story-data.js` (lihat bagian di bawah).
- Jika pemain mati, permainan dilanjutkan dari **checkpoint terakhir** yang sudah dilewati
  (bukan persis di titik kematian — supaya pemain tidak respawn di tengah jurang/air).
- Serangan besar bisa dipakai 2 kali, dan **terisi ulang otomatis setiap kali pemain mati**
  (sesuai permintaan) — jadi setelah respawn, pemain selalu punya 2 serangan besar lagi.

## Struktur file

```
action/
├── index.html         Halaman utama + semua layar (menu, cara bermain, cerita, HUD)
├── game.js             Seluruh engine: fisika, musuh, boss, peluru, level, render, HUD
├── story-data.js        Teks & path gambar untuk menu / cerita awal / cerita akhir (EDIT DI SINI)
├── assets/story/
│   ├── intro.svg         Ilustrasi cerita awal (placeholder, silakan diganti)
│   └── ending.svg         Ilustrasi cerita akhir (placeholder, silakan diganti)
└── README.md
```

## Cara mengedit CERITA & GAMBAR (menu, awal, akhir)

Buka **`story-data.js`**. Semua judul, subjudul, dan teks cerita ada di situ dalam bentuk
string biasa — tinggal diedit. Untuk gambar, ada dua cara:

1. **Paling mudah:** timpa langsung file `assets/story/intro.svg` dan `assets/story/ending.svg`
   dengan gambar Anda sendiri (boleh `.png` / `.jpg`, tinggal ganti ekstensi filenya juga di
   `story-data.js` pada bagian `image: "..."`).
2. Atau ubah path `image` di `story-data.js` agar menunjuk ke file gambar lain.

## Cara mengedit LEVEL (jurang, halangan, air, checkpoint, musuh)

Semua tata letak level ada di bagian **"DATA LEVEL"** pada awal file `game.js`, dalam bentuk
array yang mudah dibaca/diedit:

- `PITS` — daftar jurang (`x1`, `x2`, `type: 'small'|'large'`)
- `OBSTACLES` — halangan padat yang harus diloncati (`x`, `width`, `height`)
- `WATER_ZONES` — area air yang memperlambat (`x1`, `x2`)
- `CHECKPOINTS` — titik respawn (`x`)
- `ENEMY_SPAWNS` — titik & jangkauan patroli musuh biasa (`x`, `range`)
- `GATE_X`, `BOSS_SPAWN_X`, `ENEMIES_TO_BEAT_FOR_BOSS` — pengaturan gerbang & Boss

Konstanta fisika (kecepatan jalan/lari, gravitasi, kekuatan loncat, dsb.) ada tepat di atasnya
pada bagian **"KONFIGURASI DASAR"**.

## Catatan desain

- Serangan pemain berbentuk tembakan (peluru), bukan pukulan jarak dekat — jadi baik musuh
  biasa maupun Boss "mati jika kita tembak" sesuai permintaan.
- Musuh biasa mati dalam 1x tembakan. Boss punya HP (ditampilkan sebagai bar HP di atas layar)
  dan butuh beberapa kali tembakan (ditambah serangan besar) untuk dikalahkan.
- Checkpoint ditandai dengan bendera di dunia game: abu-abu jika belum dilewati, hijau jika
  sudah. Progres jumlah musuh yang dikalahkan tetap tersimpan walau pemain mati berkali-kali.
