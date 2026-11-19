# OmniGeo Engine

> **Next-Generation Mathematical Hybrid CAD/BIM & Continuous Landscape Engine**  
> *Mobil va kuchsiz GPU larda ham 60+ FPS da cheksiz detalizatsiya va 100+ km gigant landshaftni 99% kam xotira bilan chizuvchi zamonaviy grafik dvigatel.*

---

## 🎯 Asosiy Maqsad

Klassik dvigatellar (**Unreal Nanite, Unity, HOOPS, ODA, Autodesk Forge, Cesium**) quyidagi 3 ta asosiy muammo bilan chegaralangan:
1. **Og'ir xotira va CPU tiqilishi:** Barcha geometriyani oldindan millionlab statik uchburchaklarga maydalab, xotirani gigabaytlab to'ldiradi.
2. **Katta masofada titrash (Z-fighting):** 100 km li relefda oddiy FP32 8 mm gacha kvant xatolik berib, nozik CAD detallarini buzib yuboradi.
3. **Mobil va arzon GPU larda ishlamaslik:** Unreal Nanite DirectX 12 SM6.6 va desktop talab qiladi, oddiy telefonlarda qotadi.

**OmniGeo Engine** ushbu muammolarni **5 ta matematik ustun** orqali hal qiladi:

---

## 🏛️ Dvigatelning 5 ta Matematik Ustuni

1. **Continuous Geometry Clipmaps (100+ km Landshaft, < 5 MB VRAM):**
   * Kamera atrofida markazlashgan konsentrik halqalar (Clipmap levels).
   * Butun 100 km lik tog'li landshaft xotirada atigi **bir dona 64x64 lik kanonik to'rni** qayta-qayta ishlatadi.
2. **Spatial DAG & Symmetry Mathematics (339x kam VRAM):**
   * Tipik xonadonlar, deraza bloklari, eshiklar, qavatlar xotirada faqat 1 marta saqlanadi.
   * Qolgan 100+ binodagi barcha takrorlanishlar faqat $SE(3)$ affin transformatsiya matritsalari orqali havola qilinadi.
   * 100 ta bino (57.4 million vertex) xotirasi **2.76 GB dan 8.33 MB ga** tushirildi!
3. **Analitik Sirtlar va Dinamik Piksel-Zichlik Tessellation:**
   * $S(u,v) = \mathbf{C}(v) + \mathbf{N}(v)x(u) + \mathbf{B}(v)y(u)$
   * Karnizlar, plintuslar va profillar Bishop Frame (RMF) orqali burchaklarida sinmasdan, 0.00 ms CPU sarfi bilan ekran o'lchamiga mos silliqlanadi.
4. **100% GPU-Driven Culling (Compute + Hi-Z):**
   * 500 000 ta obyektni saralash CPU da 262 ms olgan bo'lsa, GPU Compute Shaderda **0.056 ms (56 mikrosekund)** da bajariladi (**4,675x tezroq**).
   * 166 000 ta alohida buyruq o'rniga bitta `MultiDrawIndexedIndirect` chaqiruvi ketadi.
5. **Relative-to-Eye (RTE) & Double-Single (DS) Aniqligi:**
   * 100 km masofada ham 0.001 mm (1 mm) li murvatlarda titrash butunlay yo'q qilinadi.

---

## 🚀 Qanday Ishga Tushiriladi?

### 1. Interaktiv 3D Veb / Mobil Ko'rish Oynasi:
Istalgan brauzerda to'g'ridan-to'g'ri ochish:
```bash
python run_engine.py
```
Yoki `web/index.html` faylini istalgan brauzerda (Chrome, Edge, Safari) ikki marta bosib oching.

### 2. Apparat Simulyatsiyalari va Benchmarklarni Qayta Ishlatish:
```bash
python sim_1_analytic_sweep.py      # Analitik karniz va dinamik tessellation
python sim_2_gpu_culling.py         # 500k obyektli GPU Compute shader testi
python sim_3_dag_instancing.py      # 100 ta bino Spatial DAG instancing
python sim_4_differential_and_fp64.py # Differensial qirralar va DS aniqlik
python generate_charts_and_report.py  # Yangi grafik va vizual tahlil
```

---

## 📁 Loyiha Strukturasi

```
d:\Geometry soft\
├── src/
│   └── engine/
│       ├── math/
│       │   ├── bishop_frame.py       # Rotation Minimizing Frame (RMF)
│       │   └── double_single.py      # Relative-to-Eye & 48-bit mantissa
│       ├── terrain/
│       │   ├── clipmap.py            # Geometry Clipmaps continuous LOD
│       │   └── heightmap_generator.py# Procedural fractal fBm noise
│       └── geometry/
│           └── spatial_dag.py        # Directed Acyclic Graph BIM instancing
├── web/
│   ├── index.html                    # 3D Real-time Interaktiv Dvigatel
│   ├── three.min.js                  # Standalone offline kutubxona
│   └── OrbitControls.js              # Offline kamera nazorati
├── benchmark_comparison.png          # Apparat testlari natijalari
├── run_engine.py                     # Dvigatelni ishga tushirish skripti
└── README.md
```
