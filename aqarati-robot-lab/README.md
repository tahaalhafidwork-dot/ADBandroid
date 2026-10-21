# Aqarati Robot AI Lab — المرحلة 3A

لوحة تحكم محلية مستقلة لمراجعة نتائج معالجة الإعلانات العقارية ومراقبة المهام واستخدام النماذج. تعمل الواجهة بالعربية وRTL، وتقرأ جميع الأرقام من SQLite؛ لا توجد بيانات عقارية تجريبية ثابتة في الواجهة.

## ما تم تنفيذه

- FastAPI مع توثيق OpenAPI ومسارات منفصلة للإحصاءات التاريخية والحية وإعدادات المزودات.
- SQLite بوضع WAL، وSQLAlchemy 2، وترحيلات Alembic.
- استيراد متحقق منه للملف المحلي `aqarati_50_results.json` مع منع التكرار ببصمة SHA-256.
- لوحة معلومات، مراجعة مسودات، مراقبة تاريخية وحية، إعدادات مزودات، مهام، وقاموس عراقي.
- إعدادات مستقبلية معطلة افتراضيًا لـKilo AI Gateway وOllama وOpenVINO؛ المرحلة 3A لا تتصل بها.
- اختيار المنفذ عبر `AQARATI_BACKEND_PORT`، مع انتقال آمن من 8000 إلى 8010 إن كان الافتراضي مشغولًا.
- React + TypeScript + Vite + Tailwind + Lucide + Recharts، بتصميم RTL متجاوب.
- عزل محلي: الخادم مربوط بـ`127.0.0.1`، مع Trusted Host وOrigin guard للعمليات المعدّلة.
- لا تشغيل لـApify أو Kilo أو OCR، ولا نشر إلى نظام عقاراتي.

## المتطلبات

- Windows 10/11
- Python 3.11 أو أحدث
- Node.js 20 أو أحدث مع npm

## التثبيت والتشغيل على Windows

افتح PowerShell داخل `aqarati-robot-lab` ونفّذ:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts\migrate_database.py
cd frontend
npm install
cd ..
```

شغّل الخادم في نافذة PowerShell أولى:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts\start_backend.py
```

وشغّل الواجهة في نافذة ثانية:

```powershell
python scripts\start_frontend.py
```

يعرض المشغّلان منفذ Backend وهدف Vite Proxy بوضوح. إذا كان 8000 مشغولًا ينتقل Backend إلى 8010 من دون إنهاء العملية الموجودة، ويقرأ Frontend المنفذ الفعلي تلقائيًا. ثم افتح `http://127.0.0.1:5173`.

لتحديد المنفذ صراحةً قبل تشغيل النافذتين:

```powershell
$env:AQARATI_BACKEND_PORT = "8010"
python scripts\start_backend.py
```

## الترحيل والنسخ الاحتياطي

على قاعدة موجودة، ينشئ الأمر التالي نسخة SQLite متسقة داخل `data/processed/backups/` قبل تطبيق Alembic:

```powershell
python scripts\migrate_database.py
```

لاختبار الترحيل على نسخة فقط، مع إبقاء الأصل دون تغيير:

```powershell
python scripts\migrate_database.py --test-copy data/processed/phase3a_test.sqlite3
$env:AQARATI_LAB_DATABASE = "data/processed/phase3a_test.sqlite3"
```

الترحيل الجديد هو `20261021_02` ويضيف إعدادات المزودات والمقاييس الحية ولا يحذف أي جدول أو بيانات استيراد.

## استيراد البيانات القديمة

ضع نسخة محلية باسم `data/legacy/aqarati_50_results.json` (أو استخدم النسخة المحلية الموجودة بلا امتداد)، ثم اضغط «استيراد البيانات القديمة» في لوحة المعلومات. يمكن كذلك استخدام:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/imports/legacy `
  -ContentType application/json `
  -Body '{"source":"aqarati_50_results.json"}'
```

لا يُعدّل المستورد ملف المصدر. الملف الخام وقاعدة البيانات مستبعدان من Git. تكرار الاستيراد يعيد `already_imported` ولا يكرر السجلات.

## الاختبارات والبناء

```powershell
python -m pytest -q
python scripts\verify_structure.py
python scripts\check_git_clean.py --staged-only
cd frontend
npm run build
```

تستخدم الاختبارات بيانات اصطناعية فقط. قاعدة التشغيل موجودة في `data/processed/aqarati_lab.sqlite3` وهي غير متتبعة في Git.

## واجهات API

| الطريقة | المسار | الغرض |
|---|---|---|
| GET | `/api/health` | صحة الخادم وقاعدة البيانات |
| GET | `/api/dashboard` | الإحصاءات والتوزيعات الفعلية |
| GET | `/api/posts` | بحث وتصفية وترتيب وتقسيم المنشورات |
| GET | `/api/posts/{id}` | النص والنتيجة والمحاولات والصور المتاحة |
| GET | `/api/listings` | مسودات العقارات |
| PATCH | `/api/listings/{id}` | تعديل محلي مع سجل مراجعة |
| GET | `/api/jobs` | سجل المهام |
| GET | `/api/models/usage` | قياسات الاستخدام التاريخية |
| GET | `/api/models/live` | القياسات الحية المنفصلة حسب المزود |
| GET | `/api/models/providers` | إعدادات المزودات الآمنة |
| PATCH | `/api/models/providers/{id}` | تعديل الإعدادات من دون اختبار اتصال |
| GET/POST | `/api/dialect/terms` | قراءة/إضافة المصطلحات |
| PATCH | `/api/dialect/terms/{id}` | تعديل واعتماد المصطلح |
| POST | `/api/imports/legacy` | استيراد المصدر المسموح |

## الأمان والخصوصية

- لا تمرر API مسار ملف يختاره المستخدم؛ اسم المصدر مقيد بقائمة صريحة.
- لا تُسجل النصوص الأصلية في رسائل الأخطاء أو أحداث النظام.
- الروابط والصور تُعرض فقط إن وجدت في المصدر، ولا يُفترض وجودها.
- القيم التاريخية غير المتاحة ترجع `null` وتظهر «غير متوفر»؛ لا تُشتق توكنات لكل منشور من إجمالي التشغيل.
- لا يحتوي مخطط SQLite أو API على حقل مفتاح API. تُحفظ الأسرار مستقبلًا في متغيرات البيئة أو مخزن أسرار محلي فقط.
- راجع [PROJECT_BOUNDARIES.md](PROJECT_BOUNDARIES.md) و[docs/architecture.md](docs/architecture.md) للتفاصيل.
