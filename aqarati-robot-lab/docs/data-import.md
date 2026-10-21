# استيراد البيانات القديمة

البيانات القديمة موجودة في مشاريع أخرى داخل المستودع. المبدأ: **لا تُعدّل المصدر أبداً**.

## الوضعان

| الوضع | السلوك | متى يُستخدم |
|---|---|---|
| `copy` | نسخ Payload إلى `data/legacy/<label>/` مع تسجيل البصمة | العمل على نسخة مستقلة داخل المشروع |
| `reference` | لا نسخ؛ تسجيل مرجع في `data/imports/manifest.json` | إبقاء المصدر كمرجع وحسب |

## الاستخدام

```bash
cd aqarati-robot-lab

# عرض المصادر المتاحة
python scripts/import_legacy_data.py --list

# نسخ ملف واحد
python scripts/import_legacy_data.py \
    --source real_estate_ai_pipeline/output/aqarati_50_results.json \
    --mode copy --name aqarati_50_results

# مرجع لمجلد كامل دون نسخ
python scripts/import_legacy_data.py \
    --source real_estate_ai_pipeline/output \
    --mode reference
```

## الضوابط المطبَّقة

1. **المصدر للقراءة فقط.** يُفتح بـ `"rb"` فقط، ويُمرَّر على `paths.ensure_read_only_source()`
   الذي يرفض أي مصدر يقع داخل جذر المشروع.
2. **تجميد المصدر.** تُحسب بصمة SHA-256 لكل ملف قبل الاستيراد وبعده، وتُلغى العملية
   إن تغيّر أي ملف.
3. **البيانات الشخصية تُتجاهل.** الملفات التي أسماؤها تحتوي `ground_truth` أو `contact`
   أو `phone` أو `secret` أو `credentials` أو `.env` لا تُستورد إلا مع `--allow-pii` الصريح.
4. **السجل بلا مسارات مطلقة.** `data/imports/manifest.json` يحتوي على مسارات نسبية لجذر
   المستودع فقط، و`write_manifest()` يرفض أي سجل يحتوي مساراً مطلقاً.
5. **الوجهة داخل المشروع فقط.** يُرفض أي مسار وجهة خارج `aqarati-robot-lab/`.

## شكل السجل

```json
{
  "version": 1,
  "imports": [
    {
      "imported_at": "2026-10-21T09:00:00+00:00",
      "mode": "copy",
      "label": "aqarati_50_results",
      "entries": [
        {
          "source": "real_estate_ai_pipeline/output/aqarati_50_results.json",
          "destination": "aqarati-robot-lab/data/legacy/aqarati_50_results/aqarati_50_results.json",
          "mode": "copy",
          "sha256": "…",
          "size": 412676,
          "modified_at": "2026-10-20T12:00:00+00:00",
          "pii_blocked": false
        }
      ],
      "skipped": []
    }
  ]
}
```

## المصادر المسموحة (قراءة فقط)

- `real_estate_ai_pipeline/output/`
- `real_estate_ai_pipeline/data/`
- `raqi_reverse_engineering/`
- `evidence/`

أي مصدر خارج هذه القائمة يُرفض ما لم يُمرَّر صراحةً مع تظل قاعدة "لا تعديل المصدر" سارية.

## البيانات المستوردة لا تُرفع إلى Git

محتوى `data/legacy/` و `data/raw/` و `data/processed/` مستبعد في `.gitignore`.
يُرفع السجل فقط لأنه بيانات وصفية وبلا مسارات مطلقة.
