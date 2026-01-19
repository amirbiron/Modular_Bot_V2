# 🚀 התחלה מהירה - Render.com

## 3 צעדים פשוטים לפריסה בענן

### ✅ שלב 1: העלה ל-GitHub (2 דקות)

```bash
cd Modular_Bot_V2
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### ✅ שלב 2: צור Web Service ב-Render (1 דקה)

1. היכנס ל-[Render.com](https://render.com)
2. **New +** → **Web Service**
3. חבר את ה-GitHub repository
4. הגדר:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn engine.app:app`
5. **Create Web Service**

### ✅ שלב 3: המתן להשקה (2-3 דקות)

Render יבנה ויפעיל את הדשבורד אוטומטית!

---

## 🎉 זהו! הדשבורד שלך חי!

תקבל URL כמו:
```
https://modular-bot-v2.onrender.com
```

---

## 📖 צריך עזרה?

ראה [DEPLOYMENT.md](DEPLOYMENT.md) למדריך מפורט עם screenshots.

---

## 🔄 עדכונים עתידיים

```bash
# עשה שינויים בקוד
git add .
git commit -m "Updated plugins"
git push

# Render יעדכן אוטומטית!
```

---

**זמן כולל: ~5 דקות** ⏱️
