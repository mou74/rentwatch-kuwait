# 🏠 مراقب شقق الإيجار – الكويت (RentWatch)

منصة شخصية تفحص كل **30 دقيقة** إعلانات شقق الإيجار في الكويت من:

| المصدر | الرابط | طريقة القراءة |
|---|---|---|
| 4Sale | q84sale.com | بيانات الصفحة (Next.js) – أحدث 80 إعلان |
| OpenSooq الكويت | kw.opensooq.com | صفحة كل منطقة مرتبة بالأحدث – 60 إعلان/منطقة |
| بوشملان | boshamlan.com | صفحة كل منطقة – 20 إعلان/منطقة |

وتطابقها مع معاييرك (في `config.json`):

- **المناطق:** السالمية، حولي، صباح السالم، سلوى (ويمكن تفعيل الرميثية/الجابرية/بيان/مشرف من `areas_suggested_disabled`)
- **الميزانية:** 300 – 400 د.ك
- **الغرف:** 3
- **التشطيب:** جديد / أول ساكن (يُكتشف من نص الإعلان: "أول ساكن"، "لم تسكن"، "تشطيب جديد"، "بناية جديدة"، "سوبر ديلوكس"… أو عمر البناء أقل من سنة)

## كيف تعمل

```
run.sh  →  python -m rentwatch run
            ├─ يجلب الإعلانات من المصادر الثلاثة
            ├─ يفلتر (منطقة + سعر + غرف + تشطيب)
            ├─ يخزّن في data/rentwatch.db ويتذكّر ما شاهده
            ├─ يرسل تنبيه لكل إعلان *جديد* مطابق (ماك / إيميل / تيليجرام)
            └─ يحدّث لوحة العرض docs/index.html
```

- **⭐ مطابقة قوية** = منطقة + سعر + 3 غرف + تشطيب جديد/أول ساكن → **تنبيه**.
- **✅ مطابقة** = منطقة + سعر + 3 غرف فقط → تظهر في اللوحة بدون تنبيه.  
  لو تريد تنبيهاً لكل المطابقات غيّر `"require_new_finish_for_alerts": false`.
- الإعلانات بدون سعر مذكور تُعتبر مطابقة (`include_unpriced`) لأن كثيراً من ملاك الكويت لا يذكرون السعر.
- الإعلانات التي لا يُفهم منها عدد الغرف تُستبعد (`include_unknown_rooms: false`).

## التشغيل على الماك

```bash
./install.sh
```
يثبّت مهمة `launchd` تعمل كل 30 دقيقة وعند تسجيل الدخول. السجل في `logs/rentwatch.log`.

لوحة العرض:
```bash
./.venv/bin/python -m rentwatch serve --open
```
ثم افتح <http://127.0.0.1:8765>. (أو افتح الملف `docs/index.html` مباشرة.)

أوامر أخرى:
```bash
./run.sh                                   # فحص واحد الآن
./.venv/bin/python -m rentwatch status     # إحصائيات
./.venv/bin/python -m rentwatch test-notify  # تنبيه تجريبي عبر القنوات المفعّلة
./uninstall.sh                             # إيقاف المهمة
```

> ⚠️ **اللاب مقفول = الماك نائم = لا فحص.** macOS يوقف كل المهام عند إغلاق الغطاء (إلا مع شاشة خارجية).
> للفحص المستمر والتنبيه على هاتفك استخدم التشغيل السحابي أدناه.

## التنبيهات

### 1) إشعار ماك
مفعّل افتراضياً (`notify.macos`). يظهر فقط عندما يكون الماك مستيقظاً.

### 2) إيميل (Gmail)
1. من حساب Gmail: **Google Account → Security → 2-Step Verification → App passwords** وأنشئ كلمة مرور تطبيق.
2. في `secrets.json` (ملف خاص لا يُرفع إلى Git؛ انسخه من `secrets.example.json`):
   ```json
   "email": {"enabled": true, "smtp_user": "you@gmail.com", "smtp_password": "xxxx xxxx xxxx xxxx", "to": "kyaan.co@gmail.com"}
   ```
3. جرّب: `./.venv/bin/python -m rentwatch test-notify`

### 3) تيليجرام (الأسرع على الهاتف)
1. في تيليجرام ابحث عن **@BotFather** → `/newbot` → انسخ الـ token.
2. أرسل أي رسالة لبوتك، ثم افتح `https://api.telegram.org/bot<TOKEN>/getUpdates` وانسخ `chat.id`.
3. في `secrets.json`: `"telegram": {"enabled": true, "bot_token": "...", "chat_id": "..."}`.

## التشغيل السحابي (يعمل واللاب مقفول) – GitHub Actions مجاناً

1. أنشئ مستودعاً **خاصاً (Private)** على GitHub وارفع هذا المجلد إليه:
   ```bash
   git init && git add -A && git commit -m "rentwatch" && git branch -M main
   git remote add origin https://github.com/<USER>/rentwatch-kuwait.git && git push -u origin main
   ```
2. في المستودع: **Settings → Secrets and variables → Actions → New repository secret** وأضف ما تريد:
   `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_TO`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
3. **Actions → RentWatch Kuwait → Run workflow** للتجربة الأولى. بعدها يعمل تلقائياً كل 30 دقيقة (`.github/workflows/watch.yml`) ويحفظ ما شاهده في المستودع.
4. (اختياري) **Settings → Pages → Branch: main / folder: /docs** لتفتح لوحة العرض من هاتفك على `https://<USER>.github.io/rentwatch-kuwait/`.

ملاحظة: الحساب المجاني يعطي 2000 دقيقة/شهر للمستودعات الخاصة؛ الفحص يستهلك ~1 دقيقة × 48/يوم ≈ 1450 دقيقة/شهر. لو اقتربت من الحد غيّر الجدول إلى `*/45` أو اجعل المستودع عاماً (غير محدود).

## تعديل المعايير
كل شيء في `config.json`. بعد أي تعديل لا تحتاج إعادة تثبيت؛ الفحص التالي يقرأ الإعدادات الجديدة.
