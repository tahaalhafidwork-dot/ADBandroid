# جدول الاكتشافات والأدلة — تطبيق راقي (Raqi)

## تعليمات القراءة
- **مستوى الثقة:** مؤكد / مرجح / مجهول / مُنفي
- **الحالة:** مثبت / مرجح / مجهول
- **المسار:** مسار الملف في APK أو في النظام

## جدول الاكتشافات

| # | الاكتشاف | الدليل | المسار | مستوى الثقة | الحالة |
|---|---------|--------|-------|------------|--------|
| 1 | اسم الحزمة: app.raqi | `adb shell pm list packages` | النظام | مؤكد | مثبت |
| 2 | اسم التطبيق المعروض: Raqi | AndroidManifest.xml `android:label="Raqi"` | res/values/strings.xml:25 | مؤكد | مثبت |
| 3 | الإصدار: 4.4.5 (code 116) | AndroidManifest.xml `versionCode="116" versionName="4.4.5"` | AndroidManifest.xml:3-4 | مؤكد | مثبت |
| 4 | إطار العمل: Flutter 3.44.2 | سلسلة نصية في libapp.so: "3.44.2 (stable)" | lib/arm64-v8a/libapp.so | مؤكد | مثبت |
| 5 | ABI أساسي: arm64-v8a | `pm dump app.raqi` `primaryCpuAbi=arm64-v8a` | النظام | مؤكد | مثبت |
| 6 | minSdk 26 / targetSdk 36 | AndroidManifest.xml `uses-sdk` | AndroidManifest.xml:12-14 | مؤكد | مثبت |
| 7 | المثبت: Google Play Store | `pm dump` `installerPackageName=com.android.vending` | النظام | مؤكد | مثبت |
| 8 | التاريخ الأول للتثبيت: 2026-06-28 | `pm dump` `firstInstallTime=2026-06-28` | النظام | مؤكد | مثبت |
| 9 | تاريخ آخر تحديث: 2026-09-30 | `pm dump` `lastUpdateTime=2026-09-30` | النظام | مؤكد | مثبت |
| 10 | نشاط رئيسي: app.raqi.MainActivity | AndroidManifest.xml activity | AndroidManifest.xml:104-161 | مؤكد | مثبت |
| 11 | روابط عميقة: raqi.app, raqi.go.link, app2111241733-login.tg.dev | AndroidManifest.xml intent-filters | AndroidManifest.xml:126-154 | مؤكد | مثبت |
| 12 | مخطط مخصص: app.raqi:// | AndroidManifest.xml intent-filter scheme | AndroidManifest.xml:155-160 | مؤكد | مثبت |
| 13 | فيسبوك Custom Tabs: fbconnect://cct.app.raqi | AndroidManifest.xml activity com.facebook.CustomTabActivity | AndroidManifest.xml:353-364 | مؤكد | مثبت |
| 14 | Firebase Cloud Messaging مدمج | خدمات ومستقبلات Firebase في AndroidManifest | AndroidManifest.xml:287-300, 445-462 | مؤكد | مثبت |
| 15 | Facebook App ID: 1220003732585196 | strings.xml `facebook_app_id` | res/values/strings.xml:155 | مؤكد | مثبت |
| 16 | Facebook Client Token: 1ecd017e56f753c68d6972355790ad50 | strings.xml `facebook_client_token` | res/values/strings.xml:156 | مؤكد | مثبت |
| 17 | Google API Key: AIzaSyBwE65H1c9ZrlhFFX1wdWYGs-AElxJisjI | strings.xml `google_api_key` | res/values/strings.xml:162 | مؤكد | مثبت |
| 18 | Google Maps API Key: AIzaSyB4rWyqnvc0gfCLsRGe5ZmA3uoieBTJQ6o | AndroidManifest.xml meta-data `com.google.android.geo.API_KEY` | AndroidManifest.xml:89-91 | مؤكد | مثبت |
| 19 | Firebase Project ID: raqi-iq | strings.xml `project_id` | res/values/strings.xml:176 | مؤكد | مثبت |
| 20 | Firebase Storage: raqi-iq.appspot.com | strings.xml `google_storage_bucket` | res/values/strings.xml:165 | مؤكد | مثبت |
| 21 | GCM Sender ID: 93107465890 | strings.xml `gcm_defaultSenderId` | res/values/strings.xml:161 | مؤكد | مثبت |
| 22 | Adjust SDK مدمج (إسناد تسويقي) | ContentProvider `com.adjust.sdk.SystemLifecycleContentProvider` | AndroidManifest.xml:541-543 | مؤكد | مثبت |
| 23 | Sentry مدمج (تتبع أخطاء) | Providers `io.sentry.android.core.SentryPerformanceProvider`, `io.sentry.ndk.SentryNdkPreloadProvider` | AndroidManifest.xml:496-499, 559-562 | مؤكد | مثبت |
| 24 | مكتبة توقيع API: libsigner.so | ملف أصلي في split APK | lib/arm64-v8a/libsigner.so | مؤكد | مثبت |
| 25 | دالة buildSignature موجودة | سلسلة نصية في libapp.so | lib/arm64-v8a/libapp.so | مؤكد | مثبت |
| 26 | نموذج YOLOv11n-seg.tflite محلي | ملف في الأصول + سلسلة نصية "YOLO seg model loaded" | assets/models/yolo11n-seg.tflite + libapp.so | مؤكد | مثبت |
| 27 | TensorFlow Lite مدمج | مكتبات libtensorflowlite_jni.so + libtensorflowlite_gpu_jni.so | lib/arm64-v8a/ | مؤكد | مثبت |
| 28 | Ultralytics YOLO مدمج | مكتبة libultralytics.so | lib/arm64-v8a/libultralytics.so | مؤكد | مثبت |
| 29 | حجم نموذج TFLite: ~11.7 ميجابايت | حجم الملف الفعلي | assets/models/yolo11n-seg.tflite | مؤكد | مثبت |
| 30 | خدمة كشف الأسعار: shouf.raqi.app/detect | سلسلة نصية "[PriceScanner] vast: opening stream to https://shouf.raqi.app/detect" | lib/arm64-v8a/libapp.so | مؤكد | مثبت |
| 31 | WebSocket آمن: wss://raqi.app | سلسلة نصية في libapp.so | lib/arm64-v8a/libapp.so | مؤكد | مثبت |
| 32 | نقطة نهاية API: /app/profile/posts | سلسلة نصية في libapp.so | lib/arm64-v8a/libapp.so | مؤكد | مثبت |
| 33 | نقطة نهاية API: /app/search | سلسلة نصية في libapp.so | lib/arm64-v8a/libapp.so | مؤكد | مثبت |
| 34 | نقطة نهاية API: /app/user-chats | سلسلة نصية في libapp.so | lib/arm64-v8a/libapp.so | مؤكد | مثبت |
| 35 | نقطة نهاية API: /media_uploads | سلسلة نصية في libapp.so | lib/arm64-v8a/libapp.so | مؤكد | مثبت |
| 36 | نقطة نهاية API: /voice-search/ | سلسلة نصية في libapp.so | lib/arm64-v8a/libapp.so | مؤكد | مثبت |
| 37 | خادم خلفي: 195.29.196.251 (cleartext HTTP) | network.xml `<domain>195.29.196.251</domain>` cleartextTrafficPermitted="true" | res/xml/network.xml:6 | مؤكد | مثبت |
| 38 | قاعدة بيانات SQLite للمحفوظات | مخطط SQL: CREATE TABLE bookmarks_new(...) | lib/arm64-v8a/libapp.so (سلسلة نصية) | مؤكد | مثبت |
| 39 | دعم اللغة العربية (خطوط NotoSansArabic) | ملفات خطوط في الأصول | assets/fonts/NotoSansArabic/ | مؤكد | مثبت |
| 40 | تكامل فيسبوك (تسجيل دخول، مشاركة، تحليل) | Facebook SDK، App ID، Client Token، AutoLogAppEvents | strings.xml، AndroidManifest | مؤكد | مثبت |
| 41 | كود كشط Facebook Marketplace داخل APK | **غير موجود** — لا يوجد كود scraping في الكود المجمع | — | **منفي** | غير موجود |
| 42 | جمع بيانات Facebook Marketplace من الخادم | غير قابل للتأكيد من APK وحده | — | مجهول | غير مؤكد |
| 43 | نموذج NLP محلي لمعالجة النصوص | **غير موجود** — لا يوجد .tflite/.onnx/.gguf لـ NLP | — | **منفي** | غير موجود |
| 44 | معالجة النصوص على الخادم | عدم وجود نموذج NLP محلي يرجح المعالجة على الخادم | — | مرجح | غير مؤكد |
| 45 | معالجة النصوص عبر قواعد تقليدية (Regex) | احتمال قائم بدون دليل مباشر | — | مرجح | غير مؤكد |
| 46 | بحث صوتي مدعوم | نقطة نهاية /voice-search/ في الكود | libapp.so | مؤكد | مثبت |
| 47 | تشغيل الوسائط (MPV) | مكتبة libmpv.so مدمجة | lib/arm64-v8a/libmpv.so | مؤكد | مثبت |
| 48 | تجربة تخطيط القائمة (list-layout) | experiment-policy.json | assets/config/experiment-policy.json | مؤكد | مثبت (تجربة معطلة) |
| 49 | تجربة إعداد مدن تلقائياً (city-autoseed) | experiment-policy.json | assets/config/experiment-policy.json | مؤكد | مثبت (تجربة معطلة) |
| 50 | الإشعارات الأولى مفعل (notif_first_run) | experiment-policy.json | assets/config/experiment-policy.json | مؤكد | مثبت |

## ملخص المستويات

| مستوى الثقة | العدد | أمثلة |
|------------|-------|--------|
| مؤكد | 45 | اسم الحزمة، الإصدار، إطار Flutter، نموذج YOLO، نقاط نهاية API، Firebase، فيسبوك SDK |
| مرجح | 4 | معالجة النصوص على الخادم، قواعد تقليدية، جمع فيسبوك من الخادم |
| مجهول | 1 | آلية جمع فيسبوك Marketplace الفعلية |
| مُنفي | 3 | كشط فيسبوك من داخل APK، نموذج NLP محلي، نموذج LLM محلي |

## الملفات المرجعية

- `RAQI_REVERSE_ENGINEERING_REPORT.md` — التقرير الكامل
- `RAQI_DATA_FLOW.md` — مخطط تدفق البيانات
- `RAQI_AI_ANALYSIS.md` — تحليل الذكاء الاصطناعي
- `AQARATI_AUTOMATED_LISTINGS_DESIGN.md` — تصميم نظام Aqarati
- `raqi_reverse_engineering/apk/` — ملفات APK المستخرجة (الأصلية)
- `raqi_reverse_engineering/jadx_output/` — مخرجات JADX (الكود المفكك)
- `raqi_reverse_engineering/native_libs/` — المكتبات الأصلية المستخرجة
