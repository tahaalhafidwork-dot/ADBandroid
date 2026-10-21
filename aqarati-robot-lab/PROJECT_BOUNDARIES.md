# حدود مشروع Aqarati Robot AI Lab

هذا الملف يحدد نطاق مشروع **Aqarati Robot AI Lab** وصلاحيات القراءة والكتابة داخل المستودع.
المشروع مستقل تماماً: لا يشارك أي ملف مع المشاريع القائمة في المستودع، وكل ما هو خارج
مجلد `aqarati-robot-lab/` يُعامَل كمصدر قراءة فقط.

---

## 1. نطاق المشروع

| البند | القيمة |
|---|---|
| مجلد المشروع | `aqarati-robot-lab/` |
| جذر المشروع | يُشتق من `backend/paths.py` عبر `Path(__file__).resolve().parent.parent` |
| جذر المستودع | يُشتق من `PROJECT_ROOT.parent` |
| المسارات المطلقة | ممنوعة داخل الكود (يفحصها `scripts/verify_structure.py`) |
| حالة المشروع | هيكل فقط — لا واجهة تحكم ولا محرك معالجة في هذه المرحلة |

## 2. صلاحيات الكتابة

الكتابة مسموحة **داخل مجلد المشروع فقط**، وتتم حصرياً عبر المساعدين المحميين في
`backend/paths.py`:

- `paths.write_text(path, content)`
- `paths.write_bytes(path, content)`
- `paths.safe_write_path(path)` — للتحقق قبل الكتابة

أي محاولة للكتابة خارج جذر المشروع تُرفض مع `paths.BoundaryError`.

| المسار | القراءة | الكتابة | ملاحظات |
|---|---|---|---|
| `aqarati-robot-lab/backend/` | مسموحة | مسموحة (عبر `paths`) | كود التطبيق |
| `aqarati-robot-lab/frontend/` | مسموحة | مسموحة (عبر `paths`) | الواجهة المستقبلية |
| `aqarati-robot-lab/data/raw/` | مسموحة | مسموحة (عبر `paths`) | بيانات خام، مستبعدة من git |
| `aqarati-robot-lab/data/processed/` | مسموحة | مسموحة (عبر `paths`) | مخرجات وقواعد بيانات، مستبعدة من git |
| `aqarati-robot-lab/data/legacy/` | مسموحة | مسموحة (عبر `paths`) | نسخ مستوردة فقط، مستبعدة من git |
| `aqarati-robot-lab/data/imports/` | مسموحة | مسموحة (عبر `paths`) | سجل الاستيراد (بيانات وصفية فقط) |
| `aqarati-robot-lab/docs/` | مسموحة | مسموحة (عبر `paths`) | التوثيق |
| `aqarati-robot-lab/scripts/` | مسموحة | مسموحة (عبر `paths`) | أدوات التشغيل |
| `aqarati-robot-lab/tests/` | مسموحة | مسموحة (عبر `paths`) | الاختبارات |

## 3. المصادر للقراءة فقط (خارج المجلد الجديد)

كل شيء خارج `aqarati-robot-lab/` غير قابل للتعديل أو الحذف أو إعادة التسمية، بما في ذلك:

- `real_estate_ai_pipeline/` (المشروع السابق ونتائجه)
- `raqi_reverse_engineering/`
- `evidence/`
- ملفات جذر المستودع وسجلات git

القواعد الملزمة:

1. **لا نقل ولا حذف ولا إعادة تسمية** لأي ملف قديم.
2. **لا الكتابة** داخل المشاريع القديمة، تحت أي ظرف.
3. استخدام `paths.ensure_read_only_source()` قبل التعامل مع أي مصدر قديم.
4. التقطيع (snapshot) اختياري: `legacy_import.import_source()` يتحقق من بصمة SHA-256 للمصدر
   قبل وبعد العملية، ويلغي العملية إذا تغيّر المصدر.

مصادر الاستيراد المسموحة حالياً (تُقرأ فقط):

- `real_estate_ai_pipeline/output/`
- `real_estate_ai_pipeline/data/`
- `raqi_reverse_engineering/`
- `evidence/`

## 4. آلية استيراد البيانات القديمة

يوفر `backend/legacy_import.py` و `scripts/import_legacy_data.py` وضعين:

| الوضع | السلوك | الاستخدام |
|---|---|---|
| `copy` | نسخ Payload إلى `aqarati-robot-lab/data/legacy/<label>/` | مساحة عمل مستقلة داخل المشروع |
| `reference` | لا نسخ، سجل فقط في `data/imports/manifest.json` | بقاء المصدر كمصدر الحقيقة |

ضوابط إضافية:

- المصدر يُفتح للقراءة فقط ولا يُكتب عليه.
- الملفات التي يشتبه بأنها بيانات شخصية (`ground_truth`، `contact`، `phone`، `secret`،
  `credentials`، `.env`) تُتجاهل افتراضياً، ولا تُستورد إلا مع `--allow-pii` الصريح.
- السجل (`data/imports/manifest.json`) يحتوي على مسارات نسبية لجذر المستودع فقط، ولا يحتوي
  مسارات مطلقة أو أسماء أجهزة.

التفاصيل: `docs/data-import.md`.

## 5. الأسرار والبيانات الحساسة

- ممنوع وضع مفاتيح API أو كلمات المرور أو ملفات `.env` داخل المشروع.
- ملفات الأسرار مستبعدة في `.gitignore` (`*.key`, `*.pem`, `credentials*`, `secrets*`).
- الأرقام الهاتفية ومعرفات المستخدمين وروابط الصور الشخصية لا تُطبع في التقارير.

## 6. الخدمات المدفوعة

- ممنوع تشغيل **Apify** أو **Kilo API** أو أي خدمة مدفوعة ضمن هذا المشروع.
- الاستيراد يعمل على ملفات JSON المحلية فقط.
- `backend/config.py` يضبط `offline=True` افتراضياً.

## 7. نظافة Git

- كل commits جديدة يجب أن تحتوي على مسارات داخل `aqarati-robot-lab/` فقط.
- `scripts/check_git_clean.py` يتحقق من ذلك آلياً:

```bash
python scripts/check_git_clean.py --staged-only
```

- نتائج التجارب السابقة وملفات الأرقام (`apify_*.json`, `logcat_raw.txt`, الصور، `evidence/`)
  تبقى في مكانها ولا تُحذف.

## 8. حدود الاختبارات

`aqarati-robot-lab/tests/` يتحقق من:

1. أن كل المسارات تُشتق من جذر المشروع وأن المسارات المطلقة ممنوعة.
2. أن الكتابة خارج المشروع مرفوضة (`BoundaryError`).
3. أن الملفات القديمة لا تُعدَّل: بصمة SHA-256 ثابتة قبل/بعد الاستيراد.
4. أن وضع النسخ لا ينسخ الملفات التي تشتبه بالبيانات الشخصية افتراضياً.
5. أن السجل لا يحتوي مسارات مطلقة.
