# تشغيل المراحل 3C + 4 + 5

الترحيل الحالي هو `20261021_04`. يضيف طابور معالجة دائم، ونتائج OCR مستقلة، وإعداد موصل Aqarati وسجل مزامنة المسودات. لا يحذف الترحيل الجداول أو البيانات، وتنشئ أداة الترحيل نسخة احتياطية متسقة قبل تعديل قاعدة التشغيل.

## التشغيل على Windows

من PowerShell داخل `aqarati-robot-lab`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts\migrate_database.py
cd frontend
npm install
cd ..
python scripts\start_backend.py
```

وفي نافذة ثانية:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts\start_frontend.py
```

افتح `http://127.0.0.1:5173`. يختار Backend المنفذ 8000 أو ينتقل إلى 8010 إذا كان الأول مشغولاً، ويستخدم Vite المنفذ الفعلي نفسه.

## مركز المعالجة

اختر منشوراً أو أكثر والمزوّد، ثم أنشئ المهمة وشغّلها. تُحفظ نتيجة كل منشور فوراً. تتوفر أوامر الإيقاف المؤقت والاستئناف والإلغاء وإعادة العناصر الفاشلة ضمن حد المحاولات. يمنع النظام إعادة منشور ناجح إلا عند إرسال `force_reprocess=true` صراحة. الحدود المتاحة هي عدد الطلبات والتوكنات والتكلفة، وتبقى القيم التي لا يبلغ عنها المزود «غير متوفر».

## Ollama وOpenVINO

اضبط عنوان loopback واسم النموذج من «إعدادات النماذج». زر الاكتشاف يفحص الخدمة المحلية فقط، ولا يشغّلها ولا ينزّل نموذجاً. العناوين الافتراضية:

- Ollama: `http://127.0.0.1:11434`
- OpenVINO بواجهة OpenAI المتوافقة: `http://127.0.0.1:8001`

يعمل التطبيق بصورة طبيعية إن لم تكن الخدمتان مثبتتين. لا يفترض وجود GPU ولا ينزّل أي نموذج.

## OCR المحلي

Tesseract مكوّن اختياري. بعد تثبيته مع حزم اللغات `ara` و`kur` و`eng` يمكن اختيار صورة منشور أو ملف نسبي داخل `data/`. تنزيل الروابط الخارجية معطل افتراضياً؛ لتفعيله مؤقتاً:

```powershell
$env:AQARATI_LAB_ENABLE_IMAGE_DOWNLOAD = "true"
```

تُرفض عناوين loopback والشبكات الخاصة، والتحويلات، والأنواع غير المدعومة، والملفات الأكبر من 5MB. نتائج OCR وتصحيحاتها مستقلة، واعتمادها لا يستبدل حقول العقار المؤكدة تلقائياً.

## Kilo AI Gateway

يبقى النموذج الافتراضي `kilo-auto/free` ولا يسمح محرك الحماية بنموذج مدفوع تلقائياً. الاتصال الحقيقي معطل افتراضياً. إذا قرر مالك المشروع تشغيله لاحقاً، يضع `KILO_API_KEY` في بيئة عملية Backend ويفعّل `AQARATI_LAB_ENABLE_CLOUD_AI_TEST=true` و`AQARATI_LAB_OFFLINE=false`، ثم يؤكد الإرسال من الواجهة. لا يُحفظ المفتاح في SQLite.

## موصل Aqarati

لم يوجد داخل المستودع عقد إنتاجي موثق لإنشاء المسودات، لذلك نُفذ موصل مستقل وفق [عقد التكامل](aqarati-integration-contract.md) واختبارات Mock. لا يدعم الموصل النشر العام. عند توفر API الإنتاجي لاحقاً:

```powershell
$secret = Read-Host "Aqarati service token" -AsSecureString
$env:AQARATI_SERVICE_TOKEN = [Net.NetworkCredential]::new("", $secret).Password
$env:AQARATI_LAB_ENABLE_AQARATI_SYNC = "true"
python scripts\start_backend.py
```

يضبط المالك عنوان HTTPS ومسار المسودات ويفعّل الإعداد من «تكامل Aqarati». كل إرسال يتطلب عقاراً معتمداً محلياً وتأكيداً صريحاً ومفتاح منع تكرار. الصور تحتاج تأكيد حقوق مستقل، والحمولة تحمل دائماً `publish: false` و`lifecycle: draft`.

## المسارات الجديدة

| الطريقة | المسار | الغرض |
|---|---|---|
| GET/POST | `/api/processing/jobs` | عرض/إنشاء مهام المعالجة الدائمة |
| POST | `/api/processing/jobs/{id}/start` | بدء المهمة |
| POST | `/api/processing/jobs/{id}/pause` | إيقاف مؤقت |
| POST | `/api/processing/jobs/{id}/resume` | استئناف |
| POST | `/api/processing/jobs/{id}/cancel` | إلغاء |
| POST | `/api/processing/jobs/{id}/retry-failed` | إعادة العناصر الفاشلة المؤهلة |
| GET | `/api/local-models/{provider}/discover` | اكتشاف محلي دون تشغيل أو تنزيل |
| GET/POST | `/api/ocr` و`/api/ocr/extract` | سجل OCR وتشغيله محلياً |
| PATCH/POST | `/api/ocr/{id}` و`/api/ocr/{id}/review` | التصحيح والمراجعة دون دمج تلقائي |
| GET/PATCH | `/api/aqarati/config` | إعداد موصل المسودات |
| GET/POST | `/api/aqarati/sync` | سجل المزامنة/إنشاء مسودة مؤكدة |
