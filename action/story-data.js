// ============================================================
// STORY-DATA.JS
// ------------------------------------------------------------
// Semua teks dan gambar di file ini BEBAS DIEDIT tanpa perlu
// menyentuh game.js sama sekali.
//
//  - Untuk mengganti TEKS: tinggal edit string di bawah.
//  - Untuk mengganti GAMBAR: ganti isi file di folder
//    assets/story/ (pertahankan nama file yang sama), ATAU
//    ubah path "image" di bawah ini ke file gambar lain
//    (mendukung .svg, .png, .jpg).
// ============================================================

const STORY_DATA = {
  // ---------- MENU UTAMA ----------
  menu: {
    title: "GARDA PERBATASAN",
    subtitle: "Sebuah Game Aksi 2D",
  },

  // ---------- CERITA AWAL (tampil sebelum permainan dimulai) ----------
  intro: {
    title: "Awal Cerita",
    image: "assets/story/intro.svg",
    text:
`Di ujung perbatasan yang sunyi, pos penjagaan terakhir diserang oleh
pasukan tak dikenal pada tengah malam.

Sebagai satu-satunya penjaga yang tersisa, kau harus menembus hutan,
jurang, dan sungai untuk mencapai markas musuh sebelum fajar tiba
dan serangan besar-besaran dimulai.

Di ujung jalan, seorang komandan musuh telah menunggu.`,
  },

  // ---------- CERITA AKHIR (tampil setelah Boss dikalahkan) ----------
  ending: {
    title: "Akhir Cerita",
    image: "assets/story/ending.svg",
    text:
`Komandan musuh akhirnya tumbang. Fajar merekah di ufuk timur, dan
pos perbatasan kembali aman.

Kau berjalan pulang dengan luka-luka, namun perbatasan -- dan
orang-orang di baliknya -- kini selamat berkat keberanianmu.

TAMAT`,
  },
};
