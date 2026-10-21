# Backend

FastAPI + SQLAlchemy 2 + SQLite/WAL. نقطة التشغيل هي `backend.main:app`، والتهيئة عبر `scripts/init_database.py`.

- `models.py`: الجداول والعلاقات.
- `schemas.py`: تحقق طلبات التعديل والاستيراد.
- `api.py`: مسارات REST والاستعلامات.
- `import_service.py`: استيراد JSON المنظم ومنع التكرار.
- `legacy_import.py`: آلية النسخ/المرجعة المحمية الموروثة من المرحلة الأولى.
- `paths.py`: حارس حدود المشروع.

لا تُضف مسار ملفات يحدده العميل، ولا تسجل النص الخام في الأخطاء.
