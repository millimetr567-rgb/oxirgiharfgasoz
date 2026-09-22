# 📚 «So‘nggi harf» — Kutubxona Intellektual O‘yini (Google Gemini AI)

**«So‘nggi harf»** — bu axborot-kutubxona faoliyati, kitobxonlik, bibliografiya, adabiyotshunoslik va nashriyot sohasiga oid atamalar bilan o'ynaladigan intellektual so'z o'yini. Dastur **Google Gemini API** sun'iy intellekti bilan to'liq integratsiya qilingan bo'lib, o'zbek lotin alifbosining o'ziga xos qoidalariga (`o‘`, `g‘`, `sh`, `ch`, `ng`) to'liq rioya qiladi.

---

## 🌟 Asosiy Xususiyatlar

1. **Google Gemini AI Integratsiyasi**:
   - Har bir kiritilgan so'zning o'zbek tilida mavjudligi, imlosi va kutubxona/kitob sohasiga aloqadorligi AI orqali tekshiriladi.
   - So'zning ilmiy va qisqa izohi (ma'nosi) ekranda ko'rsatiladi.
   - Kompyuter o'z navbatida avval boyitilgan mahalliy bazadan, yetishmaganda esa Gemini AI orqali yangi so'zlarni topadi.
2. **Qat'iy 7 Soniyalik Taymer**:
   - Har bir navbatda o'yinchiga aynan 7 soniya vaqt beriladi.
   - Katta rangli indikator (yashil ➔ to'q sariq ➔ qizil) real vaqt rejimida qolgan vaqtni ko'rsatadi.
   - 0 ga yetganda javob qabul qilish to'xtatiladi.
   - Taymer ishlashi AI so'rovlarini kutishga bog'liq emas.
3. **O'zbek Alifbosi Harflarini Mukammal Tahlil Qilish**:
   - `sh`, `ch`, `o‘`, `g‘` kabi harflar to'g'ri birikma sifatida aniqlanadi (masalan, «Shahar» -> boshlanishi `Sh`, «Chop» -> `Ch`).
   - Apostroflarning turli klaviaturalardagi variantlari (`'`, `’`, `ʻ`, `ʼ`, `` ` ``) avtomatik normallashtiriladi.
   - «Tong» kabi `ng` bilan tugaydigan so'zlarga adolatli qoida asosida `g` yoki `ng` bilan boshlanuvchi so'z aytishga ruxsat beriladi.
4. **Takroriy So'zlarni Qat'iy Bloklash**:
   - Katta-kichik harflar va bo'shliqlar normallashtiriladi.
   - O'yinda bir marta ishlatilgan so'z ikkinchi marta qabul qilinmaydi.
5. **Katta Boshlang'ich So'zlar Bazasi**:
   - Kutubxonachilik, bibliografiya, kitob turlari, adabiy janrlar, poligrafiya va elektron kutubxona bo'yicha 150 dan ortiq tasdiqlangan atamalar bazasi (SQLite va JSON).
6. **Zamonaviy Foydalanuvchi Interfeysi**:
   - PyQt6 asosidagi qulay, chiroyli qorong'u (Dark Glass) dizayn.
   - Barcha jarayonlar alohida oqimlarda (`QThread`) bajariladi, bu esa interfeys muzlab qolmasligini ta'minlaydi.
   - Buyruqlar satrida o'ynashni xush ko'ruvchilar uchun qulay **CLI rejimi** ham mavjud.

---

## 📂 Loyiha Tuzilishi

```text
d:/oxirgi harf so'z kutubxona/
├── config.py              # Konfiguratsiya va sozlamalar
├── ozbek_letters.py       # O'zbek tili harflari va apostroflarini tahlil qilish
├── word_database.py       # SQLite va JSON so'zlar bazasi boshqaruvi
├── gemini_service.py      # Google Gemini API rasmiy SDK integratsiyasi
├── word_validator.py      # 2 bosqichli tekshiruv (dasturiy + Gemini AI)
├── timer.py               # Mustaqil 7 soniyalik taymer
├── game.py                # Asosiy o'yin dvigateli (Game Engine)
├── gui.py                 # PyQt6 zamonaviy grafik foydalanuvchi interfeysi
├── main.py                # Dasturni ishga tushirish (GUI va CLI)
├── test_game.py           # Avtomatlashtirilgan unit testlar
├── requirements.txt       # Loyiha qaramliklari
├── .env.example           # Muhit o'zgaruvchilari namunasi
└── data/
    ├── library_words.json # Boshlang'ich kutubxona so'zlari
    └── library_words.db   # SQLite ma'lumotlar bazasi
```

---

## 🚀 O'rnatish va Ishga Tushirish

### 1. Talablar
- Python 3.10 yoki undan yuqori (tizimda Python 3.13 mavjud)
- Faol internet aloqasi (Gemini API uchun)

### 2. Qaramliklarni o'rnatish
Agar kerak bo'lsa, zarur paketlarni o'rnating:
```bash
pip install -r requirements.txt
```

### 3. Google Gemini API kalitini sozlash
1. `.env.example` faylidan nusxa olib, yangi `.env` fayli yarating:
   ```bash
   cp .env.example .env
   ```
2. `.env` faylini oching va `GEMINI_API_KEY` qiymatiga o'z kalitingizni kiriting:
   ```env
   GEMINI_API_KEY=AIzaSy...sizning_kalitingiz...
   GEMINI_MODEL=gemini-2.5-flash
   ```
*(Eslatma: Agar `.env` fayliga kalit kiritmagan bo'lsangiz ham, o'yin ochilganda grafik interfeysdagi **«🔑 API Kaliti»** tugmasi orqali to'g'ridan-to'g'ri kiritishingiz mumkin!)*

### 4. Dasturni ishga tushirish

#### A) Zamonaviy Grafik Interfeysda (GUI)
```bash
python main.py
```
yoki to'g'ridan-to'g'ri:
```bash
python gui.py
```

#### B) Terminal (Buyruqlar satri) Rejimida
```bash
python main.py --cli
```

### 5. Testlarni ishga tushirish
Tizimning barcha qismlarini tekshirish uchun:
```bash
python -m unittest test_game.py -v
```

---

## 🎮 O'yin Qoidalari

1. Kompyuter dastlabki kutubxona sohasiga oid so'zni aytadi (masalan, «Kutubxona»).
2. O'yinchi 7 soniya ichida shu so'zning oxirgi harfi bilan boshlanuvchi yangi kutubxona atamasini kiritishi kerak (masalan, «A» harfiga «Arxiv»).
3. Gemini AI va tizim so'zni quyidagilar bo'yicha tekshiradi:
   - So'z o'zbek tilida to'g'ri yozilganmi?
   - Soha (kutubxona, kitob, nashriyot, adabiyot) bilan bog'liqmi?
   - Harf mosmi va oldin ishlatilmaganmi?
4. Har bir to'g'ri so'z uchun ball beriladi va ketma-ketlik oshadi.
5. So'ng kompyuter o'yinchining so'zi oxirgi harfiga mos yangi so'z topadi.
6. Agar o'yinchi 7 soniyada javob bera olmasa yoki noto'g'ri so'z kiritsa, o'yin yakunlanadi.
7. Agar kompyuter mos so'z topa olmasa, o'yinchi g'olib deb e'lon qilinadi!

Maroqli va bilimli o'yin tilaymiz! 📖
