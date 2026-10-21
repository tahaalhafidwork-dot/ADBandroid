# عقد تكامل Aqarati Robot المقترح

لا يحتوي المستودع الحالي على شيفرة Backend الإنتاجية أو عقد موثوق لإنشاء إعلان. نقاط النهاية المكتشفة في تقارير التحليل تخص البحث والملف الشخصي ورفع الوسائط، كما توجد دلائل على توقيع طلبات غير موثق. لذلك لا يستخدم المختبر أياً منها للكتابة.

## الواجهة المطلوبة من فريق Aqarati

### `GET /api/robot/capabilities`

تتحقق به هوية الخدمة `Aqarati Robot`. يجب أن يعيد:

```json
{"can_create_drafts": true, "can_publish": false, "can_upload_images": false}
```

### `POST /api/robot/drafts`

الرؤوس: `Authorization: Bearer <service-token>`، و`X-Service-Identity: Aqarati Robot`، و`Idempotency-Key`.

الجسم يحمل دائمًا `"lifecycle":"draft"` و`"publish":false`. الاستجابة الناجحة تعيد `{"draft_id":"..."}`. يجب أن يعيد الخادم نفس المسودة عند تكرار مفتاح منع التكرار، وألا يمنح هوية الروبوت صلاحية نشر عام.

الصور اختيارية ولا ترسل إلا بعد تأكيد حق استخدامها. لا تحفظ الرموز في SQLite؛ يقرأ المختبر `AQARATI_SERVICE_TOKEN` من البيئة. التنفيذ الحقيقي يبقى معطلاً حتى تعيين `AQARATI_LAB_ENABLE_AQARATI_SYNC=true` وتفعيل الإعداد والتأكيد في الواجهة.
