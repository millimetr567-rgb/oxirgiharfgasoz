# 🚀 «So‘nggi harf» Dasturini Vercelga Joylashtirish (Deploy) Qo‘llanmasi

Ushbu loyiha Vercel Serverless Python (`@vercel/python`) va zamonaviy TailwindCSS veb-interfeysiga to‘liq moslashtirildi. Barcha konfiguratsiya fayllari (`vercel.json`, `api/index.py`, `public/index.html`, `requirements.txt`) tayyorlandi.

Quyidagi **2 ta qulay usuldan birini** tanlab, dasturni bir necha daqiqada Vercelga joylashtirishingiz mumkin:

---

## 1-USUL: GitHub orqali Joylashtirish (Eng qulay va tavsiya etiladigan usul)

Bu eng oson va standart usul bo‘lib, Vercel avtomatik ravishda har bir yangilanishni o‘zi deploy qilib boradi.

### 1-qadam: GitHub-da yangi repozitoriy yarating
1. [github.com/new](https://github.com/new) manziliga kiring.
2. Repozitoriy nomini yozing (masalan: `songgi-harf-kutubxona`).
3. Repozitoriyni **Public** yoki **Private** qilib yarating («Create repository»).

### 2-qadam: Loyihani GitHub-ga yuboring
Terminalda (PowerShell) quyidagi buyruqlarni ketma-ket bajaring:
```bash
git remote add origin https://github.com/SIZNING_GITHUB_USERNAME/songgi-harf-kutubxona.git
git branch -M main
git push -u origin main
```

### 3-qadam: Vercel-ga ulang
1. [vercel.com](https://vercel.com) saytiga kiring va o‘z hisobingizga kiring (GitHub orqali kirish tavsiya etiladi).
2. Bosh sahifada **«Add New...»** tugmasini bosib, **«Project»** ni tanlang.
3. Yangi yaratgan `songgi-harf-kutubxona` repozitoriyangiz yonidagi **«Import»** tugmasini bosing.
4. **Environment Variables** bo‘limiga kiring va quyidagi o‘zgaruvchini qo‘shing:
   - **Key:** `GEMINI_API_KEY`
   - **Value:** `sizning_google_gemini_api_kalitingiz`
5. **«Deploy»** tugmasini bosing!

🎉 **1 daqiqa ichida saytingiz jonli internetda ishga tushadi va sizga `https://songgi-harf-...vercel.app` ko‘rinishidagi bepul havola beriladi!**

---

## 2-USUL: Vercel CLI (Terminal) orqali Joylashtirish

Agar to‘g‘ridan-to‘g‘ri kompyuteringizdagi terminaldan yuklamoqchi bo‘lsangiz:

### 1-qadam: Vercel CLI-ni o‘rnating
```bash
npm install -g vercel
```

### 2-qadam: Vercel hisobingizga kiring
```bash
vercel login
```
*(Brauzer ochiladi va Vercel hisobingizni tasdiqlaysiz)*

### 3-qadam: Loyihani deploy qiling
Loyiha papkasida (`d:\oxirgi harf so'z kutubxona`):
```bash
vercel
```
Buyruq berilganda quyidagi savollarga javob bering:
- Set up and deploy? $\rightarrow$ **Y**
- Which scope? $\rightarrow$ [Sizning akkauntingiz]
- Link to existing project? $\rightarrow$ **N**
- Project name? $\rightarrow$ `songgi-harf` (yoki Enter)
- In which directory is your code located? $\rightarrow$ `./` (Enter bosing)

Ishlab chiqarish (Production) uchun to‘liq deploy qilish:
```bash
vercel --prod
```

### 4-qadam: API Kalitini kiritish
```bash
vercel env add GEMINI_API_KEY
```
va o‘z Gemini API kalitingizni kiriting.

---

## 💻 Mahalliy Kompyuterda Veb-Versiyani Sinab Ko‘rish

Vercelga yuklashdan oldin veb-saytni o‘z kompyuteringizda ko‘rmoqchi bo‘lsangiz:
```bash
python api/index.py
```
yoki:
```bash
uvicorn api.index:app --reload
```
Brauzerda [http://127.0.0.1:8000](http://127.0.0.1:8000) manzilini oching!
