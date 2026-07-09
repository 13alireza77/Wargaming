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
| Python | 3.10 یا بالاتر |
| Ollama | نصب‌شده و در حال اجرا |
| RAM | حداقل ۱۶ گیگابایت (برای مدل ۳B پیشنهادی) |
| سیستم‌عامل | macOS، Linux یا Windows |

## راه‌اندازی سریع

### ۱. کلون و نصب وابستگی‌ها

```bash
git clone <repository-url>
cd Wargaming
python3 -m venv .venv
source .venv/bin/activate   # در ویندوز: .venv\Scripts\activate
pip install -r requirements.txt
```

### ۲. اجرای Ollama

```bash
ollama serve
```

Ollama را **به‌صورت بومی** اجرا کنید (نه داخل Docker روی Mac)، تا از GPU استفاده شود.

### ۳. ساخت مدل و پایگاه داده

```bash
python3 manage.py migrate
python3 manage.py retrain_wargaming_llm
```

این دستور در صورت نیاز مدل پایه `qwen2.5:3b` را دانلود می‌کند و مدل سفارشی `wargaming:unified` را می‌سازد.

### ۴. اجرای سرور

```bash
python3 manage.py runserver
```

مرورگر: **http://127.0.0.1:8000/chat/**

## تست

با اجرای سرور، Ollama و مدل `wargaming:unified`:

```bash
python3 test_system.py
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
python3 manage.py retrain_wargaming_llm --force
```

3. سرور Django را ری‌استارت کنید (در صورت نیاز).

**گزینه‌های دستور:**

```bash
python3 manage.py retrain_wargaming_llm --model qwen2.5:3b --force
```

## تنظیمات مهم

فایل `war_game/project_config.py`:

| تنظیم | مقدار پیش‌فرض |
|--------|----------------|
| مدل پایه | `qwen2.5:3b` |
| مدل تحلیل | `wargaming:unified` |
| آدرس Ollama | `http://localhost:11434` |
| زبان رابط | فارسی (`fa`) |
| زمان انتظار پاسخ | ۱۸۰ ثانیه |
| حداکثر توکن خروجی | ۴۰۰ (`num_predict`) |
| پنجره زمینه | ۳۰۷۲ (`num_ctx`) |

## عیب‌یابی

| مشکل | راه‌حل |
|------|--------|
| `Cannot connect to Ollama` | `ollama serve` را اجرا کنید |
| پاسخ timeout | اولین درخواست کند است؛ صبر کنید یا `num_predict` را در config کم کنید |
| مدل پیدا نشد | `ollama list` و سپس `retrain_wargaming_llm --force` |
| پاسخ انگلیسی | سؤال را به فارسی بپرسید؛ system prompt فارسی است |
| کندی شدید | برنامه‌های دیگر را ببندید؛ مدل ۳B حدود ۲–۳ گیگ RAM می‌خواهد |

```bash
ollama list
ollama ps
```

## مجوز

صرفاً برای اهداف آموزشی و پژوهشی.
