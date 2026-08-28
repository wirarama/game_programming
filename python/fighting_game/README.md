# Fighting Game (Pygame) — Pilih Tokoh, Kalahkan Semua Lawan

Game fighting 2D dengan menu pilih tokoh. Kamu memilih satu tokoh, lalu bertarung
satu-per-satu melawan SEMUA tokoh lain secara berurutan. Kalahkan semuanya untuk
melihat layar ending dengan gambar dan teks kemenangan tokohmu.

## Menjalankan

```bash
pip install pygame
python main.py
```

## Kontrol

- `A` / `D` : gerak kiri/kanan
- `W` : lompat
- `F` : pukul
- `G` : tendang
- `ENTER` : lanjut ke lawan berikutnya (setelah menang) / kembali ke menu (di layar ending)
- `R` : coba lagi (setelah kalah)
- `M` : kembali ke layar pilih tokoh (setelah kalah)
- `ESC` : keluar

## Menambah tokoh baru (jumlah bebas, tanpa edit kode)

Semua tokoh didefinisikan di `data/characters.json`, dalam list `"characters"`.
Tambahkan blok baru dengan format:

```json
{
  "id": "nama_unik_tanpa_spasi",
  "name": "Nama Tampilan",
  "color": [R, G, B],
  "images": {
    "standby": "assets/images/nama_unik/standby.png",
    "jump":    "assets/images/nama_unik/jump.png",
    "punch":   "assets/images/nama_unik/punch.png",
    "kick":    "assets/images/nama_unik/kick.png"
  },
  "stats": { "health": 100, "speed": 5, "punch_damage": 6, "kick_damage": 10 },
  "ending": {
    "image": "assets/images/nama_unik/ending.png",
    "text": "Teks yang muncul saat tokoh ini menjadi juara."
  }
}
```

Lalu taruh 5 file gambar (standby, jump, punch, kick, ending) di folder
`assets/images/nama_unik/` dengan nama file sesuai JSON. Jika gambar belum ada,
game tetap berjalan normal dengan kotak placeholder berlabel nama file.

Tidak ada batas jumlah tokoh — tambahkan sebanyak yang kamu mau.

## Menentukan tokoh yang selalu jadi lawan terakhir (Boss)

Di bagian paling atas `data/characters.json`:

```json
"final_boss_id": "shadow_master"
```

Ganti nilainya dengan `id` tokoh manapun di daftar `characters`. Tokoh tersebut akan
SELALU menjadi lawan terakhir yang dihadapi, berapapun jumlah tokoh dan siapapun yang
kamu mainkan. Kalau kamu memilih tokoh boss itu sendiri untuk dimainkan, dia otomatis
tidak ikut dalam antrean lawan (karena tidak melawan dirinya sendiri).

## Struktur folder

```
fighting_game/
  main.py                    -> semua logika game & tampilan
  data/characters.json         -> daftar tokoh, stat, path gambar, teks ending, final_boss_id
  assets/images/<id>/           -> gambar tiap tokoh: standby.png, jump.png, punch.png, kick.png, ending.png
```

## Menyeimbangkan game

Ubah `health`, `speed`, `punch_damage`, `kick_damage` per tokoh di `data/characters.json`
untuk mengatur tingkat kesulitan masing-masing lawan. Tidak perlu mengubah kode Python.
