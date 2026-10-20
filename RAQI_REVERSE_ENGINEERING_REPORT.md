# تقرير الهندسة العكسية لتطبيق راقي (Raqi)

## 1. ملخص تنفيذي

تم إجراء هندسة عكسية استكشافية شاملة لتطبيق Android باسم "راقي" (Raqi)، الإصدار 4.4.5 (versionCode 116)، المثبت على جهاز Samsung Galaxy S25 (SM-S918B) عبر Wireless ADB على العنوان `192.168.1.62:36881`.

تطبيق راقي هو تطبيق Flutter يستهلك بيانات من خادم خلفي خاص به، مع تكاملات لفيسبوك (تسجيل دخول، مشاركة، تحليلات)،.Firebase (إشعارات، تخزين)، Sentry (تتبع أخطاء)، وAdjust SDK (إسناد تسويقي). يستخدم النموذج الذكي YOLOv11-seg عبر TensorFlow Lite لمعالجة الصور محلياً، ويستخدم WebSocket للتحديثات اللحظية.

**الاستنتاج الرئيسي:** لا يوجد دليل على أن التطبيق يكشف بيانات Facebook Marketplace مباشرة من داخل APK. البيانات تأتي من خلفية خاصة بالتطبيق (`raqi.app`، `shouf.raqi.app`، `195.29.196.251`). عملية جمع بيانات Facebook Marketplace (إن وجدت) تحدث من جانب الخادم، خارج نطاق التطبيق.

---

## 2. معلومات التطبيق الأساسية

| الحقل | القيمة |
|-------|--------|
| اسم الحزمة | `app.raqi` |
| اسم التطبيق المعروض | Raqi |
| الإصدار | 4.4.5 |
| رمز الإصدار | 116 |
| minSdk | 26 |
| targetSdk | 36 |
|compileSdk | 36 |
| المثبت | com.android.vending (Google Play Store) |
| تاريخ التثبيت الأول | 2026-06-28 |
| تاريخ آخر تحديث | 2026-09-30 |
| ABI أساسي | arm64-v8a |
| الإطار | Flutter (إصدار 3.44.2) |
| التوقيع | Google Play Store |

### ملفات APK المستخرجة

| الملف | الحجم (بайт) | SHA-256 |
|-------|-------------|---------|
| base.apk | 23,608,307 | A7CC12AB8D299BCE589F585C2EE7077EBB78FCFE792E349D224CFCFE8BA8C410 |
| split_config.ar.apk | 37,273 | E8FDF7FBF7F206CF65C2B4C9965FC961C1FE13C6E53446B1894E3FD510774CE2 |
| split_config.arm64_v8a.apk | 49,829,372 | A516DBD3DB456A2BF31D60C44F3EB5953AF2B2CBC08B017D318D9E33C911E4CD |
| split_config.en.apk | 53,657 | 034D4C94C561B2AF6A1B65E4DCA6490AF1C9FAAFA5A8017290E8AB8D39B62983 |
| split_config.tr.apk | 33,177 | 563ED534D0BE17A88E4B35D6F3F70D004C345644254EC2061038775F981B4DFF |
| split_config.xxhdpi.apk | 272,378 | AD8FBD24B3AEC505813103AEFF9719F9BF7E3A9AAA07AC3CDB8B8CD4A4FA2BCB |

---

## 3. البنية العامة (AndroidManifest.xml)

### المكونات الرئيسية

**Activities:**
- `app.raqi.MainActivity` — النشاط الرئيسي (Flutter)، مع فلترات Intent لروابط عميقة:
  - `https://raqi.app/app` (موثق، AutoVerify)
  - `https://raqi.go.link` (موثق، AutoVerify)
  - `https://app2111241733-login.tg.dev` (موثق، AutoVerify)
  - `app.raqi://` (مخطط مخصص)
  - `fbconnect://cct.app.raqi` (فيسبوك Custom Tabs)
- `com.facebook.FacebookActivity`
- `com.facebook.CustomTabActivity`
- `com.facebook.CustomTabMainActivity`
- `io.flutter.plugins.urllauncher.WebViewActivity`
- `com.google.android.play.core.common.PlayCoreDialogWrapperActivity`

**Services:**
- `com.bbflight.background_downloader.UIDTJobService` — مزيل خلفي (JobService، معد للتصدير)
- `com.baseflow.geolocator.GeolocatorLocationService` — خدمة تحديد الموقع (نوع: location)
- `io.flutter.plugins.firebase.messaging.FlutterFirebaseMessagingService` — Firebase FCM
- `io.flutter.plugins.firebase.messaging.FlutterFirebaseMessagingBackgroundService`
- `com.google.firebase.messaging.FirebaseMessagingService`
- `androidx.work.impl.foreground.SystemForegroundService` — نوع: dataSync
- `androidx.work.impl.background.systemjob.SystemJobService`

**Broadcast Receivers:**
- `app.raqi.OtpCodeReceiver` — استلام رمز OTP من واتساب (مُصدّر)
- `app.raqi.OtpErrorReceiver` — خطأ OTP من واتساب (مُصدّر)
- `com.bbflight.background_downloader.NotificationReceiver` — إشعارات التنزيل
- `io.flutter.plugins.firebase.messaging.FlutterFirebaseMessagingReceiver` — FCM
- `com.google.firebase.iid.FirebaseInstanceIdReceiver` — Firebase Instance ID
- `com.facebook.CurrentAccessTokenExpirationBroadcastReceiver` — فيسبوك توكن انتهاء الصلاحية
- `com.facebook.AuthenticationTokenManager$CurrentAuthenticationTokenChangedBroadcastReceiver`
- `androidx.work.impl.background.systemalarm.RescheduleReceiver` — عمل بعد إعادة التشغيل
- `androidx.work.impl.diagnostics.DiagnosticsReceiver`
- `androidx.profileinstaller.ProfileInstallReceiver`

**Content Providers:**
- `app.raqi.adjust-lifecycle-provider` — Adjust SDK
- `app.raqi.androidx-startup` — AndroidX Startup
- `app.raqi.flutter.share_provider` — مشاركة الملفات
- `app.raqi.flutterfirebasemessaginginitprovider` — Firebase
- `app.raqi.firebaseinitprovider` — Firebase
- `app.raqi.SentryPerformanceProvider` — Sentry
- `app.raqi.SentryNdkPreloadProvider` — Sentry NDK
- `app.raqi.FacebookInitProvider` — فيسبوك
- `app.raqi.com.bbflight.background_downloader.fileprovider` — مزيل خلفي
- `app.raqi.flutter.image_provider` — اختيار الصور

### الأذونات المطلوبة

`INTERNET`, `ACCESS_NETWORK_STATE`, `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`, `CAMERA`, `RECORD_AUDIO`, `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_DATA_SYNC`, `READ_MEDIA_IMAGES`, `READ_MEDIA_VIDEO`, `READ_MEDIA_VISUAL_USER_SELECTED`, `READ_PHONE_STATE`, `READ_BASIC_PHONE_STATE`, `POST_NOTIFICATIONS`, `VIBRATE`, `WAKE_LOCK`, `RECEIVE_BOOT_COMPLETED`, `READ_EXTERNAL_STORAGE` (maxSdk 32), `WRITE_EXTERNAL_STORAGE` (maxSdk 28), وأذونات إعلانات Google (AD_ID, TOPICS, CUSTOM_AUDIENCE, ATTRIBUTION).

### النطاقات العميقة (Deep Links)

| النطاق | المخطط | المسار | حالة التحقق |
|-------|--------|--------|-------------|
| raqi.app | http, https | /app | موثق (AutoVerify) |
| raqi.go.link | https | — | 1024 |
| app2111241733-login.tg.dev | https | — | موثق |
| app.raqi | مخصص | — | — |
| fbconnect | — | host: cct.app.raqi | فيسبوك |

---

## 4. الاتصال بالشبكة

### إعدادات أمان الشبكة (network.xml)

```xml
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">10.0.2.2</domain>
        <domain includeSubdomains="false">195.29.196.251</domain>
    </domain-config>
</network-security-config>
```

**ملاحظة:** 명확text HTTP مسموح لـ `195.29.196.251` — هذا يشير إلى خادم خلفي يقبل اتصالاً غير مشفر. النطاق `10.0.2.2` هو محاكي أندرويد (تطوير).

### نقاط نهاية API المكتشفة

| نقطة النهاية | الوصف |
|-------------|--------|
| `/app/profile/posts` | منشورات المستخدم |
| `/app/search` | البحث |
| `/app/user-chats` | الدردشات |
| `/media_uploads` | رفع الوسائط |
| `/voice-search/` | بحث صوتي |
| `wss://raqi.app` | WebSocket آمن للتحديثات اللحظية |
| `https://shouf.raqi.app/detect` | كاشف الأسعار (Price Scanner) — إرسال صور للكشف |
| `raqi/config` | إعدادات التطبيق |
| `register-push-token` | تسجيل توكن الإشعارات (FCM) |
| `chat/user-chats` | دردشة المستخدمين |

### النطاقات والنطاقات الفرعية

| النطاق | الغرض |
|-------|-------|
| raqi.app | النطاق الأساسي للتطبيق (موثق) |
| shouf.raqi.app | خدمة كشف الأسعار بالصور ("شوف" = انظر بالعربية) |
| raqi.go.link | روابط قصيرة |
| app2111241733-login.tg.dev | تسجيل دخول تيليجرام |
| cct.app.raqi | فيسبوك Custom Tabs |
| raqi-iq.appspot.com | Firebase Storage |
| 195.29.196.251 | خادم خلفي (cleartext HTTP) |

### مفاتيح API والعناوين

| المفتاح | القيمة |
|-------|--------|
| Facebook App ID | 1220003732585196 |
| Facebook Client Token | 1ecd017e56f753c68d6972355790ad50 |
| Google API Key | AIzaSyBwE65H1c9ZrlhFFX1wdWYGs-AElxJisjI |
| Firebase Project ID | raqi-iq |
| Firebase Storage Bucket | raqi-iq.appspot.com |
| GCM Sender ID | 93107465890 |
| Google Maps API Key | AIzaSyB4rWyqnvc0gfCLsRGe5ZmA3uoieBTJQ6o |

### المكتبات الخارجية المدمجة

| المكتبة | الغرض |
|--------|-------|
| Firebase (Analytics, Messaging, Installations, Crash Reporting) | إشعارات، تحليلات، تتبع أخطاء |
| Facebook SDK | تسجيل الدخول، المشاركة، التحليلات، SSO |
| Sentry (Android + NDK) | تتبع الأخطاء والأداء |
| Adjust SDK | الإسناد التسويقي (Attribution) |
| WorkManager | مهام خلفية مجدولة |
| Cronet (Google) | عميل HTTP محسّن |
| geolocator (baseflow) | خدمة تحديد الموقع |
| image_picker | اختيار الصور من المعرض/الكاميرا |
| share_plus | مشاركة المحتوى |
| flutter_map | خرائط تفاعلية |
| media_kit / mpv | تشغيل الوسائط والفيديو |
| record_web | تسجيل الصوت |
| wakelock_plus | منع دخول الجهاز في وضع السكون |

---

## 5. معالجة البيانات

### قاعدة البيانات المحلية (SQLite)

تم العثور على مخطط قاعدة بيانات في الكود:

```sql
CREATE TABLE bookmarks_new(
    post_id TEXT NOT NULL,
    bookmark_date_time TEXT,
    post_data TEXT,
    type TEXT NOT NULL DEFAULT 'bookmark',
    PRIMARY KEY (post_id, type)
)
```

هذا يشير إلى تخزين المحفوظات محلياً مع بيانات المنشور والنوع والتاريخ.

### وظائف معالجة البيانات المكتشفة

- **Parsing:** تحليل نتائج البحث، تحليل الروابط العميقة (deeplink URI parsing)
- **Normalization:** تحليل وتطبيع العناوين والبيانات
- **Categorization:** تصنيف الإعلانات (من خلال أيقونات المنزل، فئات العقارات)
- **Filtering:** فلترة نتائج البحث
- **Deduplication:** إزالة التكرارات (إشارة إلى "Stage-2 dedup" في الكود)
- **Image Processing:** معالجة الصور باستخدام YOLOv11-seg
- **Search Indexing:** فهرسة البحث (نقاط نهاية `/app/search`)
- **Data Synchronization:** مزامنة البيانات عبر WorkManager وForeground Service

### مكتبات ومكونات مرتبطة بالبيانات

- `androidx.room.MultiInstanceInvalidationService` — Room Database
- `com.bbflight.background_downloader` — تنزيل خلفي للملفات
- `io.flutter.plugins.imagepicker` — اختيار الصور
- `dev.fluttercommunity.plus.share` — مشاركة الملفات

---

## 6. تقييم مرحلة جمع Facebook Marketplace

### الأدلة على التكامل مع فيسبوك

1. **Facebook SDK مدمج:** App ID `1220003732585196`، Client Token `1ecd017e56f753c68d6972355790ad50`
2. **تسجيل دخول فيسبوك:** `FacebookLoginView`, `Log in with Facebook`, `Continue with Facebook`
3. **مشاركة فيسبوك:** `Share link`, `Copy link`, `Open in browser`
4. **فلترة فيسبوك:** `fbconnect://cct.app.raqi` — Custom Tabs لفيسبوك
5. **تحليلات فيسبوك:** `AutoLogAppEventsEnabled=true`, `CodelessDebugLogEnabled=true`
6. **استعلام عن حزمة فيسبوك:** `<package android:name="com.facebook.katana"/>`

### الأدلة على جمع Facebook Marketplace من داخل التطبيق

**لا يوجد دليل** على وجود كود كشط (scraping) لـ Facebook Marketplace داخل APK. لا توجد مؤشرات على:
- استخدام Facebook Graph API لقراءة Marketplace
- Browser Automation لتصفح Marketplace
- Web Scraping لصفحات Facebook
- معالجة post scraping من فيسبوك داخل الكود المجمع

### الاستنتاج حول آلية جمع البيانات

التطبيق **لا يجمع بيانات Facebook Marketplace مباشرة**. البيانات تأتي من:

1. **خادم خلفي خاص بالتطبيق** (`raqi.app`، `195.29.196.251`) — عبر نقاط نهاية API REST
2. **WebSocket آمن** (`wss://raqi.app`) — للتحديثات اللحظية
3. **Firebase Storage** (`raqi-iq.appspot.com`) — للتخزين السحابي للوسائط

**عملية جمع بيانات Facebook Marketplace (إن وجدت) تحدث من جانب الخادم، خارج نطاق APK.** لا يمكن استنتاج آلية الجمع الفعلية من التحليل الثابت للتطبيق وحده.

---

## 7. تحليل الذكاء الاصطناعي ومعالجة النصوص

### النماذج الذكية المحلية (مؤكدة)

| النموذج | المسار | الحجم | الصيغة | الغرض |
|--------|-------|-------|--------|-------|
| YOLOv11n-seg | `assets/models/yolo11n-seg.tflite` | 11,766,231 بايت (~11.2 ميجابايت) | TensorFlow Lite | تجزئة كائنات الصور (Segmentation) |

### المكتبات الذكية المدمجة

| المكتبة | المسار | الحجم | الغرض |
|--------|-------|-------|-------|
| TensorFlow Lite JNI | `lib/arm64-v8a/libtensorflowlite_jni.so` | 4.3 ميجابايت | تشغيل نماذج TFLite |
| TensorFlow Lite GPU | `lib/arm64-v8a/libtensorflowlite_gpu_jni.so` | 2.5 ميجابايت | تسريع GPU لـ TFLite |
| Ultralytics YOLO | `lib/arm64-v8a/libultralytics.so` | 344 كيلوبايت | نموذج YOLO من Ultralytics |
| Sentry NDK | `lib/arm64-v8a/libsentry.so` | 752 كيلوبايت | تتبع الأخطاء (ليست AI) |

### evidences لاستخدام النموذج الذكي

1. سلسلة النص في `libapp.so`: `"YOLO seg model loaded"` — تأكيد تحميل نموذج YOLO للتجزئة
2. سلسلة النص: `"Failed to load model"` — معالجة خطأ تحميل النموذج
3. سلسلة النص: `"[PriceScanner] vast: opening stream to https://shouf.raqi.app/detect"` — إرسال الصور إلى خادم للكشف عن الأسعار
4. ملف النموذج موجود في الأصول: `assets/models/yolo11n-seg.tflite`

### معالجة النصوص واللغة العربية

**خطوط عربية مدمجة:**
- `assets/fonts/NotoSansArabic/NotoSansArabic-*.ttf` (جميع الأوزان: Thin, Light, Regular, Medium, SemiBold, Bold, ExtraBold, Black)

**عدم وجود:**
- ملف `.tflite` أو `.onnx` لمعالجة اللغة الطبيعية (NLP)
- ملف `.gguf` أو `.safetensors` لنموذج لغوي كبير (LLM)
- ملف قاموس أو معجم عربي
- نموذج ترجمة أو تلخيص نصي محلي

### استنتاج معالجة النصوص

1. **معالجة الصور (YOLOv11-seg):** تتم محلياً على الجهاز باستخدام TensorFlow Lite
2. **كشف الأسعار من الصور:** يتم إرسال الصور إلى `https://shouf.raqi.app/detect` على الخادم
3. **معالجة النصوص والعناوين:** لا دليل على نموذج NLP محلي. المعالجة تتم إما على الخادم أو عبر قواعد تقليدية (Regex)
4. **تطبيع العناوين العربية:** لا دليل على معالج خاص للغة العربية ما وراء الخطوط المدمجة للعرض

---

## 8. مستويات الثقة في الاكتشافات

| الاكتشاف | مستوى الثقة | الدليل |
|---------|------------|--------|
| تطبيق Flutter، إصدار 4.4.5، حزمة app.raqi | مؤكد | pm dump، AndroidManifest |
| خادم خلفي على raqi.app و 195.29.196.251 | مؤكد | AndroidManifest، strings.xml، network.xml |
| WebSocket wss://raqi.app | مؤكد | سلسلة نصية في libapp.so |
| نموذج YOLOv11-seg.tflite محلي | مؤكد | ملف موجود في الأصول، سلسلة نصية في الكود |
| TensorFlow Lite مدمج | مؤكد | مكتبات .so موجودة |
| فيسبوك لتسجيل الدخول والمشاركة فقط | مؤكد | App ID، Client Token، Facebook SDK في الكود |
| جمع Facebook Marketplace من داخل التطبيق | **مُنفي** | لا يوجد كود كشط في APK |
| معالجة النصوص على الخادم | مرجح | عدم وجود نموذج NLP محلي |
| كشف الأسعار من الصور عبر shouf.raqi.app | مؤكد | سلسلة نصية في libapp.so |
| قاعدة بيانات SQLite محلية للمحفوظات | مؤكد | مخطط SQL في الكود |

---

## 9. الفجوات والمجهول

1. **آلية جمع Facebook Marketplace الفعلية:** غير قابلة للاستنتاج من APK. تحدث على الخادم على الأرجح.
2. **معالجة النصوص والعناوين:** غير مؤكد ما إذا كانت على الخادم أو محلياً عبر قواعد تقليدية.
3. **بيانات API الكاملة (طلب/استجابة):** غير مرئية بدون التقاط شبكة ديناميكي.
4. **منطق الأعمال في Dart:** الكود مجمّع في libapp.so ولا يمكن قراءته بسهولة بدون reverse engineering للنواة الأصلية.
5. **نموذج التسعير (buildSignature):** دالة التوقيع موجودة في libsigner.so لكن خوارزميتها غير معروفة.

---

## 10. ملخص архитектурية

تطبيق راقي هو مستهلك لبيانات من خلفية خاصة، مع معالجة صور محلية (YOLOv11-seg) وتكاملات خارجية (فيسبوك، Firebase، Sentry، Adjust). لا يقوم بكشط بيانات من فيسبوك مباشرة.
