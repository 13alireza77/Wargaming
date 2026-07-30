# سامانه مشاوره رزم‌افزاری خاورمیانه

سیستم مشاوره نظامی مبتنی بر Django که با یک مدل محلی Ollama، داده‌های جغرافیا، نیروی انسانی و تسلیحات را ترکیب می‌کند و به زبان فارسی پاسخ می‌دهد.

## این پروژه چه کاری انجام می‌دهد؟

- رابط گفتگوی فارسی (RTL) برای پرسش درباره سناریوهای نظامی
- یک مدل واحد `wargaming:unified` روی Ollama
- مشاوره مقایسه‌ای کشورها، زمین‌شناسی، نیروها و تسلیحات
- پاسخ‌های مبتنی بر داده‌های ساختاریافته (نه حدس آزاد)

## پیش‌نیازها

| مورد | نسخه / توضیح |
|------|----------------|
| Git | آخرین نسخه پایدار |
| Python | 3.10 یا بالاتر |
| pip + venv | برای نصب وابستگی‌ها در محیط مجازی |
| Ollama | آخرین نسخه پایدار |
| RAM | حداقل ۱۶ گیگابایت (برای مدل ۱۲B پیشنهادی؛ سرور GPU با ۲۴GB VRAM ایده‌آل است) |
| GPU | اختیاری ولی توصیه‌شده (مثلاً RTX 3090)؛ بدون GPU هم با Ollama اجرا می‌شود ولی کندتر است |
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

### ۴) مهاجرت دیتابیس و ساخت مدل مشاوره

```bash
python manage.py migrate
python manage.py retrain_wargaming_llm
```

این مرحله در صورت نیاز مدل پایه `gemma3:12b` را دانلود می‌کند و مدل سفارشی `wargaming:unified` را می‌سازد.

### ۵) اجرای سرور Django

```bash
python manage.py runserver
```

برای دسترسی از بیرون روی سرور GPU (bind به همه اینترفیس‌ها):

```bash
gunicorn war_game.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 300
```

مرورگر: **http://127.0.0.1:8000/chat/** (یا `http://<SERVER_IP>:8000/chat/`)

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

سه فایل JSON منبع اصلی مشاوره هستند:

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
python manage.py retrain_wargaming_llm --model gemma3:12b --force
```

## تنظیمات مهم

فایل `war_game/project_config.py`:

| تنظیم | مقدار پیش‌فرض |
|--------|----------------|
| مدل پایه | `gemma3:12b` |
| مدل مشاوره | `wargaming:unified` |
| آدرس Ollama | `http://localhost:11434` |
| زبان رابط | فارسی (`fa`) |
| زمان انتظار پاسخ | ۳۰۰ ثانیه |
| حداکثر توکن خروجی | ۸۰۰ (`num_predict`) |
| پنجره زمینه | ۸۱۹۲ (`num_ctx`) |

## عیب‌یابی

| مشکل | راه‌حل |
|------|--------|
| `Cannot connect to Ollama` | `ollama serve` را اجرا کنید |
| پاسخ timeout | اولین درخواست کند است؛ صبر کنید یا `num_predict` را در config کم کنید |
| مدل پیدا نشد | `ollama list` و سپس `retrain_wargaming_llm --force` |
| پاسخ انگلیسی | سؤال را به فارسی بپرسید؛ system prompt فارسی است |
| کندی شدید | روی CPU مدل ۱۲B سنگین است؛ از GPU با Ollama بومی استفاده کنید؛ `ollama ps` باید VRAM را نشان دهد |

```bash
ollama list
ollama ps
nvidia-smi
```

## استقرار آنلاین با Docker (سرور با اینترنت)

روی سروری که اینترنت دارد، یک اسکریپت همه چیز را با `curl` نصب و سرویس را بالا می‌آورد:

```bash
curl -fsSL https://raw.githubusercontent.com/13alireza77/Wargaming/main/docker-install-online.sh | sudo bash
```

با GPU و host مشخص:

```bash
curl -fsSL https://raw.githubusercontent.com/13alireza77/Wargaming/main/docker-install-online.sh \
  | sudo bash -s -- --gpu --allowed-hosts "SERVER_IP,localhost,127.0.0.1"
```

یا بعد از کلون:

```bash
git clone https://github.com/13alireza77/Wargaming.git
cd Wargaming
sudo bash docker-install-online.sh --gpu
```

اسکریپت به‌ترتیب:

1. در صورت نیاز `curl` را نصب می‌کند
2. Docker را با `curl -fsSL https://get.docker.com | sh` نصب می‌کند
3. سورس را با `git clone` (یا در نبود git با tarball از GitHub) می‌گیرد
4. imageهای Docker را می‌سازد/می‌کشد و `docker compose up` می‌زند
5. مدل `gemma3:12b` را داخل Ollama دانلود می‌کند
6. اپ مدل `wargaming:unified` را می‌سازد

Chat UI: `http://SERVER_IP:8000/chat/`

مسیر پیش‌فرض نصب: `/opt/wargaming`

## استقرار آفلاین با Docker

با Docker تنها نیاز سرور **Docker** است (از قبل نصب‌شده). سه اسکریپت:

| اسکریپت | محل اجرا | کار |
|---------|----------|-----|
| `docker-build-offline.sh` | ماشین آنلاین | ساخت بسته imageها + مدل‌ها |
| `docker-upload-offline.sh` | ماشین آنلاین | آپلود بسته به سرور با SCP |
| `docker-run-offline.sh` | سرور | لود و اجرا — **بدون اینترنت** |

> سرور واقعی آفلاین هیچ چیزی از اینترنت دانلود نمی‌کند. مدل‌ها داخل بسته ساخته می‌شوند.

### ۰) پیش‌نیاز سرور: نصب Docker (یک‌بار)

اگر روی سرور خطا می‌گیرید `docker not found`، اول Docker را نصب کنید.
روی سرور تست (که اینترنت دارد):

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
docker --version
docker compose version
```

روی سرور واقعی آفلاین، Docker باید از قبل نصب شده باشد.

### ۱) ساخت بسته (ماشین آنلاین)

```bash
cd Wargaming
bash docker-build-offline.sh --output-dir ./offline-dist
```

> اگر روی Mac (Apple Silicon / ARM) بیلد می‌کنید، اسکریپت به‌صورت پیش‌فرض `linux/amd64` می‌سازد تا روی سرورهای معمولی x86_64 اجرا شود. بسته قبلی ARM را دور بیندازید و دوباره بیلد کنید.

خروجی: `offline-dist/wargaming-docker-offline-YYYYmmdd-HHMMSS.tar.gz` (حجم بزرگ، چند گیگابایت)

### ۲) آپلود به سرور

```bash
bash docker-upload-offline.sh \
  --bundle-file ./offline-dist/wargaming-docker-offline-YYYYmmdd-HHMMSS.tar.gz \
  --server 85.208.254.201 \
  --user root
```

| پارامتر | توضیح |
|---------|--------|
| `--bundle-file` | مسیر بسته (اجباری) |
| `--server` | IP یا hostname سرور (اجباری) |
| `--user` | کاربر SSH |
| `--port` | پورت SSH (پیش‌فرض ۲۲) |
| `--identity` | مسیر کلید خصوصی SSH |
| `--remote-dir` | مسیر مقصد روی سرور (پیش‌فرض `/opt/wargaming-offline`) |

### ۳) اجرا روی سرور (بدون اینترنت)

```bash
ssh root@SERVER_IP
cd /opt/wargaming-offline

sudo bash docker-run-offline.sh \
  --bundle-file ./wargaming-docker-offline-YYYYmmdd-HHMMSS.tar.gz \
  --allowed-hosts "SERVER_IP,localhost,127.0.0.1"
```

با GPU:

```bash
sudo bash docker-run-offline.sh \
  --bundle-file ./wargaming-docker-offline-YYYYmmdd-HHMMSS.tar.gz \
  --allowed-hosts "SERVER_IP,localhost,127.0.0.1" \
  --gpu
```

| پارامتر | توضیح |
|---------|--------|
| `--bundle-file` | مسیر بسته روی سرور |
| `--install-dir` | مسیر استخراج/اجرا (پیش‌فرض `/opt/wargaming-offline`) |
| `--allowed-hosts` | لیست hostهای Django |
| `--gpu` | فعال‌سازی GPU NVIDIA |
| `--skip-start` | فقط لود imageها |

Chat UI: `http://SERVER_IP:8000/chat/`

### استفاده روزمره روی سرور

```bash
cd /opt/wargaming-offline
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.override.yml"

$COMPOSE ps
$COMPOSE logs -f app
$COMPOSE restart
$COMPOSE down
$COMPOSE up -d
```

### توسعه محلی با Docker

```bash
docker compose up --build -d
# Chat UI: http://localhost:8000/chat/
```

### متغیرهای محیطی قابل تنظیم

| متغیر | مقدار پیش‌فرض | توضیح |
|--------|----------------|--------|
| `DJANGO_ALLOWED_HOSTS` | `*` | لیست hostهای مجاز (CSV) |
| `DJANGO_SECRET_KEY` | کلید پیش‌فرض | کلید رمزنگاری Django |
| `DJANGO_DEBUG` | `0` | حالت debug |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | آدرس Ollama |
| `OLLAMA_WAIT_SECONDS` | `30` | زمان انتظار برای آماده شدن Ollama |
| `DATABASE_PATH` | `db.sqlite3` | مسیر فایل دیتابیس |

### پیش‌نیاز سرور

فقط **Docker** (+ `docker compose`).

## مجوز

صرفاً برای اهداف آموزشی و پژوهشی.
