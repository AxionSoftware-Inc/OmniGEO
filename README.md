# OmniGeo Research Engine

> **Eksperimental Ilmiy Prototip:** Matematik analitik geometriya (SDF Raymarching), Relative-to-Eye (RTE) koordinata aniqligi va apparat chegaralari tadqiqoti.

---

## 🎯 Loyihaning Asl Maqsadi va Haqiqiy Mohiyati

Ushbu loyiha zamonaviy 3D grafik dvigatellarning fundamental fizik va matematik cheklovlarini tadqiq qilish uchun yaratilgan:
1. **FP32 Kvant Titrashi (Jitter / Z-Fighting):** Katta masofalarda (100+ km) oddiy 32-bitli suzuvchi vergul mantissasi 6 mm dan 6 sm gacha xatolik berishi va buni **Relative-to-Eye (RTE)** orqali yengish yo'llari.
2. **Poligonlar Xotirasi Chegarasi (VRAM Exhaustion):** 1 milliard uchburchakni to'g'ridan-to'g'ri (raw) GPU ga yuklash jismonan 26+ GB VRAM talab qilishi va apparatni qulatishi.
3. **Piksellarga Asoslangan Analitik Geometriya (SDF Raymarching):** Uchburchaklar to'riga tayanmasdan, matematik sirtlar orqali faqat ekrandagi piksellarni hisoblash ($O(\text{piksellar})$ narxi).

---

## 📊 Apparat Sinovlari Natijalari (NVIDIA GeForce RTX 3060 12GB)

Loyihadagi `empirical_reality_test.py` skripti orqali bevosita apparatda o'lchangan haqiqiy fizik ko'rsatkichlar:

### 1. Masofa Oshishi Bilan FP32 Aniqlikning Yo'qolishi:
* **1 m:** $0.00006\text{ mm}$ (Mikroskopik aniqlik)
* **100 m:** $0.006\text{ mm}$ (Barqaror)
* **1 km:** $0.06\text{ mm}$ (Sub-millimetr)
* **100 km:** **$5.96\text{ mm}$ (~6 mm!)** &mdash; Nozik murvatlar va qirralar titraydi.
* **1,000 km:** **$59.6\text{ mm}$ (~6 sm!)** &mdash; Devorlar va relyeflar bir-biriga kirib ketadi (Z-fighting).

### 2. Uchburchaklar Soni va VRAM Sig'imi:
* **10 Million tris:** 0.26 GB VRAM
* **100 Million tris:** 2.61 GB VRAM
* **250 Million tris:** 6.52 GB VRAM (RTX 3060 54% yuklama)
* **500 Million tris:** 13.04 GB VRAM &mdash; **💥 CUDA Out of Memory (OOM)!**
* **1 Milliard tris:** 26.08 GB VRAM &mdash; Oddiy iste'molchi GPU lariga sig'maydi.

---

## 🚀 Prototiplarni Ishga Tushirish

### 1. Singularity Engine (Sof Matematik Analitik Raymarching):
Uchburchaklarsiz (0 Bayt mesh xotirasi bilan) ekrandagi piksellarni analitik formulalar orqali hisoblovchi interaktiv WebGL2 prototipi:
* Brauzerda oching: `http://localhost:8080/singularity_engine.html`
* Yoki faylni to'g'ridan-to'g'ri bosing: `web/singularity_engine.html`

### 2. Apparat Fizikasi Testi (RTX 3060 Benchmark):
```bash
python empirical_reality_test.py
```
Ushbu skript GPU xotirasi, FP32 xatoligi va xotira o'tkazuvchanligi bo'yicha haqiqiy `empirical_reality_benchmark.png` grafigini yaratadi.

### 3. Veb Serverni Ishga Tushirish:
```bash
python run_engine.py
```

---

## 📁 Loyiha Strukturasi

```
d:\Geometry soft\
├── src/engine/
│   ├── math/
│   │   ├── bishop_frame.py       # Rotation-Minimizing Frame (RMF)
│   │   └── double_single.py      # Relative-to-Eye & FP64 emulation
│   ├── terrain/
│   │   └── clipmap.py            # Geometry Clipmaps prototipi
│   └── geometry/
│       └── spatial_dag.py        # Directed Acyclic Graph prototipi
├── web/
│   ├── singularity_engine.html   # Analitik SDF Raymarching WebGL2
│   ├── index.html                # 3D Sahna Ko'rish Oynasi
│   ├── three.min.js              # Three.js kutubxonasi
│   └── OrbitControls.js          # Kamera nazorati
├── empirical_reality_test.py     # RTX 3060 real apparat testi
├── empirical_reality_benchmark.png # Real test grafigi
└── README.md
```
