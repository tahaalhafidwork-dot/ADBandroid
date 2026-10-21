# data/

بيانات **Aqarati Robot AI Lab**. كل ما هنا مستبعد من git عدا `data/imports/manifest.json`.

| المجلد | المحتوى | في git؟ |
|---|---|---|
| `raw/` | البيانات الخام كما وصلت | لا |
| `processed/` | المخرجات وقواعد البيانات المحلية | لا |
| `legacy/` | نسخ مستوردة من المشاريع القديمة | لا |
| `imports/` | سجل الاستيراد (بصمات ومسارات نسبية) | نعم (السجل فقط) |

الكتابة داخل هذه المجلدات تتم حصرياً عبر `backend/paths.py`، والاستيراد يتم عبر
`backend/legacy_import.py` أو `scripts/import_legacy_data.py`.
