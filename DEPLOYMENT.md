# מדריך פריסה ל-Render.com 🚀

מדריך מפורט לפריסת Modular Bot V2 בענן.

## 📋 דרישות מקדימות

1. חשבון GitHub (חינם)
2. חשבון Render.com (חינם)
3. הקוד שלך מוכן בפרויקט זה

---

## 🎯 שלב 1: הכנת הקוד ל-GitHub

### 1.1 צור Repository חדש ב-GitHub

1. היכנס ל-[GitHub](https://github.com)
2. לחץ על **New repository**
3. תן שם לrepository: `modular-bot-v2`
4. סמן ✅ **Public** או **Private** (לבחירתך)
5. לחץ **Create repository**

### 1.2 העלה את הקוד

```bash
# פרוק את ה-ZIP והיכנס לתיקייה
cd Modular_Bot_V2

# אתחל Git
git init

# הוסף את כל הקבצים
git add .

# צור commit
git commit -m "Initial commit - Modular Bot V2"

# שנה את שם הענף ל-main
git branch -M main

# חבר ל-GitHub (החלף YOUR_USERNAME ו-YOUR_REPO)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# דחוף את הקוד
git push -u origin main
```

### 1.3 וודא שכל הקבצים עלו

הקבצים החשובים שצריכים להיות ב-repo:
- ✅ `requirements.txt`
- ✅ `Procfile`
- ✅ `render.yaml`
- ✅ `runtime.txt`
- ✅ `engine/app.py`
- ✅ `plugins/`
- ✅ `templates/`

---

## 🌐 שלב 2: פריסה ב-Render.com

### 2.1 צור Web Service

1. היכנס ל-[Render Dashboard](https://dashboard.render.com)
2. לחץ על **New +** למעלה
3. בחר **Web Service**

### 2.2 חבר את GitHub

1. לחץ על **Connect GitHub**
2. אשר את החיבור
3. בחר את ה-repository שיצרת: `modular-bot-v2`

### 2.3 הגדר את השרת

מלא את הפרטים הבאים:

| שדה | ערך |
|-----|-----|
| **Name** | `modular-bot-v2` (או כל שם אחר) |
| **Environment** | `Python 3` |
| **Region** | `Frankfurt (EU Central)` (או קרוב אליך) |
| **Branch** | `main` |
| **Root Directory** | השאר ריק |
| **Runtime** | `Python` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn engine.app:app` |

### 2.4 בחר תוכנית

- בחר ב-**Free** (חינם!)
- לחץ **Create Web Service**

---

## ⏳ שלב 3: המתן לפריסה

### מה קורה עכשיו?

1. **Building** - Render מוריד את הקוד ומתקין את התלויות (~2-3 דקות)
2. **Starting** - השרת מתחיל לרוץ (~30 שניות)
3. **Live** - הדשבורד שלך פעיל! 🎉

### תראה לוגים כמו:

```
==> Cloning from GitHub...
==> Running build command...
Collecting Flask==3.0.0
Collecting gunicorn==21.2.0
...
==> Build successful!
==> Starting web service...
✅ Plugin loaded: hello_world
🚀 Starting Modular Bot Dashboard
📡 Server running on http://0.0.0.0:10000
```

---

## 🎉 שלב 4: גישה לדשבורד

### קבל את כתובת האתר

ב-Render Dashboard תראה:
```
https://modular-bot-v2.onrender.com
```

**פתח את הכתובת הזו בדפדפן!** 🚀

---

## 🔧 הגדרות נוספות (אופציונלי)

### משתני סביבה

אם תרצה להוסיף משתני סביבה:

1. ב-Render Dashboard, לך ל-**Environment**
2. לחץ **Add Environment Variable**
3. הוסף:
   - `DEBUG` = `False`
   - `SECRET_KEY` = `<מפתח-אקראי-כאן>`

### עדכונים אוטומטיים

כל פעם שתעשה `git push` ל-GitHub, Render יעדכן אוטומטית! ✨

```bash
# עשה שינויים בקוד
git add .
git commit -m "Added new plugin"
git push

# Render יעדכן אוטומטית!
```

---

## ⚠️ הגבלות תוכנית חינם

### Free Tier ב-Render:

- ✅ **750 שעות חינם** לחודש
- ⏸️ **כיבוי אוטומטי** אחרי 15 דקות חוסר פעילות
- 🐌 **Cold Start** - טעינה של 30-60 שניות בטעינה ראשונה
- 🔄 **Auto-sleep** - נכבה אם אף אחד לא משתמש
- 🌍 **HTTPS חינם** - כלול אוטומטית

### איך לשמור על השרת ער?

אם רוצה שהשרת יהיה תמיד פעיל, תצטרך:
1. לשדרג ל-Starter Plan ($7/חודש)
2. או להשתמש ב-uptime monitor (כמו [UptimeRobot](https://uptimerobot.com))

---

## 🐛 פתרון בעיות נפוצות

### 1. "Application failed to respond"

**פתרון:**
- וודא ש-`Procfile` קיים עם: `web: gunicorn engine.app:app`
- וודא ש-`requirements.txt` כולל את `gunicorn`

### 2. "Build failed"

**פתרון:**
- בדוק את הלוגים ב-Render
- וודא ש-`requirements.txt` תקין
- וודא שכל הקבצים עלו ל-GitHub

### 3. "502 Bad Gateway"

**פתרון:**
- זה normal אחרי cold start
- חכה 30-60 שניות
- רענן את הדף

### 4. פלאגינים לא נטענים

**פתרון:**
- וודא שהתיקייה `plugins/` עלתה ל-GitHub
- וודא ש-`config.py` מכיל את רשימת הפלאגינים
- בדוק לוגים ב-Render

---

## 📊 ניטור ולוגים

### צפייה בלוגים

1. היכנס ל-Render Dashboard
2. לחץ על השרת שלך
3. לחץ על **Logs** בתפריט
4. תראה לוגים בזמן אמת! 📈

### Metrics (תוכנית Starter ומעלה)

- CPU Usage
- Memory Usage
- Response Time
- Request Count

---

## 🎓 טיפים מתקדמים

### 1. Custom Domain

ב-Render Dashboard:
1. לך ל-**Settings** → **Custom Domain**
2. הוסף את הדומיין שלך
3. עדכן DNS records

### 2. Scheduled Restarts

כדי למנוע cold starts:
- השתמש ב-cron job שיבצע ping כל 10 דקות
- או שדרג ל-Starter Plan

### 3. Database Integration

אם תוסיף MongoDB/PostgreSQL:
1. צור database ב-Render
2. הוסף connection string ל-Environment Variables
3. עדכן את `config.py`

---

## 📚 משאבים נוספים

- [תיעוד Render](https://render.com/docs)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)

---

## 💡 זקוק לעזרה?

אם נתקעת:
1. בדוק לוגים ב-Render
2. קרא את הודעות השגיאה
3. חפש ב-[Render Community](https://community.render.com/)
4. פתח Issue ב-GitHub של הפרויקט

---

**בהצלחה! 🚀**

הדשבורד שלך עכשיו חי בענן! 🌐
