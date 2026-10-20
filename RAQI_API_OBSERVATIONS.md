# ملاحظات واجهات برمجة التطبيقات (API) — تطبيق راقي (Raqi)

## 1. نقاط نهاية API المكتشفة (من التحليل الثابت)

تم تحديد النقاط التالية من سلاسل نصية في `libapp.so` (التقرير المرحلة 1):

| نقطة النهاية | الغرض المتوقع | المصدر | مستوى الثقة |
|-------------|--------------|--------|------------|
| `/app/profile/posts` | منشورات الملف الشخصي | libapp.so | مؤكد |
| `/app/search` | البحث عن العقارات | libapp.so | مؤكد |
| `/app/user-chats` | محادثات المستخدمين | libapp.so | مؤكد |
| `/media_uploads` | رفع الوسائط | libapp.so | مؤكد |
| `/voice-search/` | البحث بالصوت | libapp.so | مؤكد |
| `/config` | إعدادات التطبيق | libapp.so | مؤكد |

## 2. خدمات خارجية

| الخدمة | الرابط | الغرض | المصدر |
|--------|--------|--------|--------|
| WebSocket آمن | `wss://raqi.app` | تحديثات لحظية | libapp.so |
| خدمة كشف الأسعار | `https://shouf.raqi.app/detect` | صور → أسعار | libapp.so |
| Firebase Storage | `raqi-iq.appspot.com` | تخزين الوسائط | strings.xml |
| Firebase Cloud Messaging | Firebase | الإشعارات | AndroidManifest |
| Facebook SDK | فيسبوك | تسجيل دخول، مشاركة، تحليلات | strings.xml |

## 3. ملاحظة حركة الشبكة الديناميكية

تم مراقبة التطبيق أثناء التشغيل عبر `dumpsys connectivity` و `dumpsys netstats`:

- التطبيق يحتفظ باتصالات شبكة نشطة (UID 10397)
- طلبات نشطة متعددة: REQUEST ids 2777, 2780, 3116
- استماع على اتصالات: LISTEN id 2778
- جميع الاتصالات مصنفة كـ `INTERNET&NOT_RESTRICTED&TRUSTED`

**القيود:** لا يمكن الاطلاع على محتوى استجابات HTTPS بسبب التشفير وعدم إمكانية interception دون تجاوز حماية التطبيق.

## 4. توقيع الطلبات

من التحليل الثابت:
- مكتبة `libsigner.so` موجودة في APK
- دالة `buildSignature` موجودة في `libapp.so`
- هذا يشير إلى أن الطلبات تُوقع قبل الإرسال للخادم

## 5. 명확 HTTP

من `network.xml`:
- نطاق `195.29.196.251` يسمح بـ cleartext HTTP
- هذا النطاق غير مرتبط بنطاقات API الأساسية المعروفة (`raqi.app`, `shouf.raqi.app`)

## 6. الاستنتاج

| السؤال | الملاحظة | الاستنتاج | مستوى الثقة |
|--------|---------|---------|------------|
| هل التطبيق يتصل بخوادم خلفية؟ | اتصالات شبكة نشطة من UID 10397 | نعم | CONFIRMED |
| هل يمكن قراءة محتوى API؟ | HTTPS مشفر، لا interception مسموح | لا | CONFIRMED (قيود) |
| هل هناك نقاط نهاية للبحث والعقارات؟ | `/app/search`, `/app/profile/posts` في libapp.so | نعم | CONFIRMED (ثابت) |
| هل الطلبات موقعة؟ | `libsigner.so`, `buildSignature` | نعم | CONFIRMED (ثابت) |
