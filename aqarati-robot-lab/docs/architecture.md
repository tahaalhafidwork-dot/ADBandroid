# معمارية المرحلة 3A

## التدفق

`legacy JSON (قراءة فقط) → تحقق/تطبيع → SQLAlchemy → SQLite/WAL → FastAPI → React RTL`

## الطبقات

- `backend/paths.py`: حدود المسارات والكتابة داخل المشروع.
- `backend/import_service.py`: قائمة المصادر المسموحة، التحقق من أشكال JSON، البصمات، والاستيراد الذري.
- `backend/models.py`: الجداول التسعة المطلوبة وعلاقاتها.
- `backend/api.py`: الاستعلامات، pagination، التعديلات المدققة، والإحصاءات المحسوبة.
- `backend/main.py`: التطبيق، العزل المحلي، CORS، وحارس Origin.
- `backend/ports.py`: اختيار منفذ loopback ونشر المنفذ الفعلي محليًا لـVite.
- `backend/migrations.py`: نسخ SQLite Backup API ثم تشغيل Alembic.
- `alembic/`: مخطط قاعدة البيانات القابل للترحيل.
- `frontend/src/`: عميل React لا يحتوي أرقام عقارية ثابتة.

## قرارات البيانات

المنشور هو كيان المصدر الوحيد. المسودة ترتبط به واحدًا لواحد. العناصر المعلمة كمكررة تُحفظ كمنشورات لأغراض التدقيق والإحصاء، لكنها لا تنشئ مسودات مراجعة ثانية. سجلات استخدام النموذج إجماليات تشغيل تاريخية، ولا توزع التوكنات حسابيًا على المنشورات.

الحقول الغائبة تبقى `NULL`. صفحة التفاصيل تفرق بين غياب الحقل في المصدر وعدم وجود مسودة بسبب فشل الاستخراج. تعديل المسودة لا يغير النص الأصلي، ويسجل الفرق في `review_actions`.

## فصل القياسات

- `model_usage` يحتفظ بقياسات التشغيل التاريخية ويُوسم بـ`metric_scope`.
- `provider_runtime_metrics` مخصص للقياسات الحية ولا يحتوي صفوفًا وهمية عند عدم تشغيل مزود.
- `ai_provider_configs` يحتفظ بإعدادات التشغيل فقط ولا يحتوي عمودًا للأسرار.
- لوحة المعلومات تعرض المنشورات ومحاولات المعالجة وطلبات API كوحدات مستقلة.

## الأمان

الخادم Loopback فقط، والـHost محصور في localhost، والعمليات المعدلة تتحقق من Origin إذا أرسله العميل. لا يوجد مسار API عام للملفات. مصدر الاستيراد اسم مسموح فقط، ويُحل داخليًا إلى `data/legacy/` أو المصدر التاريخي المحدد للقراءة فقط.
# Phase 3B single-post experiment boundary

`backend/ai_tests.py` is the control plane for a single explicitly selected source post. It reads the original only from local SQLite, redacts contact identifiers, builds a versioned prompt from approved dialect terms, and invokes an injected provider exactly once. Automated tests replace that provider dependency with an in-memory mock.

`backend/providers/kilo.py` is a non-streaming OpenAI-compatible adapter. It accepts only official Kilo HTTPS gateway hosts, follows no redirects, configures no retries, reads its bearer credential only from `KILO_API_KEY`, and never exposes that value through API schemas or database columns.

`ai_test_runs` and `ai_test_reviews` are isolated from `listing_drafts`. A partial unique SQLite index permits only one `pending` or `running` experiment globally. Idempotency keys prevent duplicate sends. Historical listing data remains immutable; reviews affect only the experiment record and term suggestions do not enter the approved dictionary automatically.

Raw provider text is redacted again, capped at 32 KiB, kept locally for seven days, and lazily purged after expiry. Structured results and audit metadata remain available.

Cloud execution requires all of: enabled Kilo configuration, official endpoint, an explicitly free model identifier, `AQARATI_LAB_OFFLINE=false`, `AQARATI_LAB_ENABLE_CLOUD_AI_TEST=true`, an environment credential, a current preview fingerprint, and three explicit user acknowledgements. Missing token or cost data remains null.
