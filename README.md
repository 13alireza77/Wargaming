# سامانه تحلیل رزم‌افزاری خاورمیانه

سیستم تحلیل نظامی مبتنی بر Django که با یک مدل محلی Ollama، داده‌های جغرافیا، نیروی انسانی و تسلیحات را ترکیب می‌کند و به زبان فارسی پاسخ می‌دهد.

## این پروژه چه کاری انجام می‌دهد؟

- رابط گفتگوی فارسی (RTL) برای پرسش درباره سناریوهای نظامی
- یک مدل واحد `wargaming:unified` روی Ollama
- تحلیل مقایسه‌ای کشورها، زمین‌شناسی، نیروها و تسلیحات
- پاسخ‌های مبتنی بر داده‌های ساختاریافته (نه حدس آزاد)

## پیش‌نیازها

| مورد | نسخه / توضیح |
|------|----------------|
| Git | آخرین نسخه پایدار |
| Python | 3.10 یا بالاتر |
| pip + venv | برای نصب وابستگی‌ها در محیط مجازی |
| Ollama | آخرین نسخه پایدار |
| RAM | حداقل ۱۶ گیگابایت (برای مدل 8B پیشنهادی) |
| سیستم‌عامل | macOS، Linux یا Windows |

## نصب روی سیستم خام (بدون پیش‌نیاز)

### ۱) نصب ابزارهای پایه

#### macOS (با Homebrew)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew update
brew install git python ollama
```

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv curl
curl -fsSL https://ollama.com/install.sh | sh
```

#### Windows (PowerShell + winget)

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.12 -e
winget install --id Ollama.Ollama -e
```

> بعد از نصب در ویندوز، یک PowerShell جدید باز کنید تا `python` و `git` در PATH قابل استفاده باشند.

### ۲) بررسی نصب بودن ابزارها

```bash
git --version
python3 --version
pip3 --version
ollama --version
```

در ویندوز اگر `python3` نبود، از `python` و اگر `pip3` نبود، از `pip` استفاده کنید.

## راه‌اندازی پروژه (از صفر)

### ۱) کلون پروژه

```bash
git clone <repository-url>
cd Wargaming
```

### ۲) ساخت محیط مجازی و نصب وابستگی‌ها

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### ۳) اجرای Ollama

```bash
ollama serve
```

Ollama را **به‌صورت بومی** اجرا کنید (نه Docker روی macOS) تا شتاب‌دهی سخت‌افزاری بهتر باشد.

### ۴) مهاجرت دیتابیس و ساخت مدل تحلیل

```bash
python manage.py migrate
python manage.py retrain_wargaming_llm
```

این مرحله در صورت نیاز مدل پایه `aya-expanse:8b` را دانلود می‌کند و مدل سفارشی `wargaming:unified` را می‌سازد.

### ۵) اجرای سرور Django

```bash
python manage.py runserver
```

مرورگر: **http://127.0.0.1:8000/chat/**

### ۶) تست سریع سلامت سیستم

```bash
python test_system.py
```

## تست

با اجرای سرور، Ollama و مدل `wargaming:unified`:

```bash
python test_system.py
```

## API گفتگو

**آدرس:** `POST /chat/api/chat/`

**بدنه درخواست:**

```json
{
  "message": "ایران و اسرائیل را از نظر زمینی مقایسه کن",
  "conversation_id": "اختیاری-uuid"
}
```

**پاسخ:**

```json
{
  "success": true,
  "reply": "...",
  "sources": ["geography", "personnel", "weapons"],
  "conversation_id": "..."
}
```

**نمونه با curl:**

```bash
curl -X POST http://localhost:8000/chat/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "قدرت نظامی ایران و ترکیه را مقایسه کن"}'
```

## ساختار پروژه

```
Wargaming/
├── orchestrator/          # اپ Django: رابط کاربری، API، سرویس LLM، مسیریاب پیام
├── data/                  # داده‌های JSON (جغرافیا، نیرو، تسلیحات)
│   ├── geography/
│   ├── personnel/
│   └── weapons/
├── war_game/              # تنظیمات Django و project_config
├── manage.py
└── requirements.txt
```

## داده‌ها

سه فایل JSON منبع اصلی تحلیل هستند:

| فایل | محتوا |
|------|--------|
| `data/geography/middle_east_geography.json` | زمین، آب‌وهوا، گلوگاه‌ها |
| `data/personnel/middle_east_personnel.json` | نیرو، ذخیره، ساختار فرماندهی |
| `data/weapons/middle_east_weapons.json` | تسلیحات و موجودی کشورها |

**کشورهای پوشش‌داده‌شده:** سوریه، عراق، ایران، اسرائیل، لبنان، اردن، عربستان، یمن، مصر، ترکیه

جزئیات ساختار داده در [data/README.md](data/README.md) آمده است.

## به‌روزرسانی داده یا مدل

1. فایل JSON مربوطه را ویرایش کنید.
2. مدل را دوباره بسازید:

```bash
python manage.py retrain_wargaming_llm --force
```

3. سرور Django را ری‌استارت کنید (در صورت نیاز).

**گزینه‌های دستور:**

```bash
python manage.py retrain_wargaming_llm --model aya-expanse:8b --force
```

## تنظیمات مهم

فایل `war_game/project_config.py`:

| تنظیم | مقدار پیش‌فرض |
|--------|----------------|
| مدل پایه | `aya-expanse:8b` |
| مدل تحلیل | `wargaming:unified` |
| آدرس Ollama | `http://localhost:11434` |
| زبان رابط | فارسی (`fa`) |
| زمان انتظار پاسخ | ۳۰۰ ثانیه |
| حداکثر توکن خروجی | ۵۰۰ (`num_predict`) |
| پنجره زمینه | ۴۰۹۶ (`num_ctx`) |

## عیب‌یابی

| مشکل | راه‌حل |
|------|--------|
| `Cannot connect to Ollama` | `ollama serve` را اجرا کنید |
| پاسخ timeout | اولین درخواست کند است؛ صبر کنید یا `num_predict` را در config کم کنید |
| مدل پیدا نشد | `ollama list` و سپس `retrain_wargaming_llm --force` |
| پاسخ انگلیسی | سؤال را به فارسی بپرسید؛ system prompt فارسی است |
| کندی شدید | برنامه‌های دیگر را ببندید؛ مدل 8B به RAM بیشتری نیاز دارد (معمولاً ۸ گیگ یا بیشتر فقط برای مدل) |

```bash
ollama list
ollama ps
```

## مجوز

صرفاً برای اهداف آموزشی و پژوهشی.
