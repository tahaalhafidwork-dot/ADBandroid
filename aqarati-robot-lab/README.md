# Aqarati Robot AI Lab

بنية مستقلة تماماً لمشروع **Aqarati Robot AI Lab** داخل المستودع.
كل شيء خارج هذا المجلد يُعامل كمصدر **قراءة فقط**، ولا يتم نقل أو حذف أو إعادة تسمية
لأي ملف قديم.

> **الحالة الحالية:** هيكل فقط. لم تُبنَ واجهة التحكم ولا محرك المعالجة بعد، حتى لا تختلط
> التجارب السابقة بالمشروع الجديد.

## البنية

```
aqarati-robot-lab/
├── backend/            كود التطبيق ومسارات الجذر وحماية حدود الكتابة
│   ├── app/            مكان واجهة التحكم ومحرك المعالجة (لاحقاً)
│   ├── config.py       إعدادات مشتقة من جذر المشروع
│   ├── legacy_import.py آلية استيراد البيانات القديمة (نسخ / مرجع)
│   └── paths.py        حل المسارات + حارس حدود الكتابة
├── frontend/           واجهة التحكم (لاحقاً)
├── data/
│   ├── raw/            بيانات خام (مستبعدة من git)
│   ├── processed/      مخرجات ومعالجات (مستبعدة من git)
│   ├── legacy/         نسخ مستوردة من المشاريع القديمة (مستبعدة من git)
│   └── imports/        سجل الاستيراد (بيانات وصفية، يُتتبَّع في git)
├── docs/               التوثيق: البنية، الاستيراد، الحدود
├── scripts/            أدوات التشغيل والتحقق
└── tests/              اختبارات حدود الكتابة وعدم تعديل الملفات القديمة
```

## البدء السريع

```bash
cd aqarati-robot-lab

# 1) التحقق من البنية وعدم وجود مسارات مطلقة
python scripts/verify_structure.py

# 2) تشغيل الاختبارات
python -m unittest discover -s tests -t . -v

# 3) عرض المصادر القديمة المتاحة للاستيراد (قراءة فقط)
python scripts/import_legacy_data.py --list

# 4) استيراد ملف (نسخ) أو مرجع بلا نسخ
python scripts/import_legacy_data.py --source real_estate_ai_pipeline/output/aqarati_50_results.json --mode copy
python scripts/import_legacy_data.py --source real_estate_ai_pipeline/output --mode reference

# 5) التحقق من أن التغييرات محصورة داخل المجلد الجديد
python scripts/check_git_clean.py --staged-only
```

## قواعد المسارات

- كل المسارات تُشتق من جذر المشروع عبر `backend/paths.py` (لا مسارات مطلقة ولا مسارات مرتبطة
  بجهاز المطور).
- الكتابة مسموحة داخل المشروع فقط، وتتم عبر `paths.write_text` / `paths.write_bytes`.
- أي محاولة كتابة خارج المشروع تُرفض بـ `paths.BoundaryError`.

التفاصيل الكاملة في [PROJECT_BOUNDARIES.md](PROJECT_BOUNDARIES.md).

## التوثيق

- [PROJECT_BOUNDARIES.md](PROJECT_BOUNDARIES.md) — النطاق وصلاحيات الوصول
- [docs/architecture.md](docs/architecture.md) — طبقات البنية
- [docs/data-import.md](docs/data-import.md) — آلية استيراد البيانات القديمة
