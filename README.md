# Modular Bot V2 🚀

תשתית פייתון מודולרית לדשבורד בוט עם מערכת פלאגינים דינמית.

## 📁 מבנה הפרויקט

```
Modular_Bot_V2/
├── config.py              # קונפיגורציה מרכזית
├── run.py                 # נקודת כניסה להפעלת השרת
├── README.md              # קובץ זה
├── DEPLOYMENT.md          # מדריך פריסה מפורט ל-Render.com
├── requirements.txt       # תלויות Python
├── Procfile               # הגדרות Gunicorn ל-Render
├── render.yaml            # קובץ הגדרות Render (deployment אוטומטי)
├── runtime.txt            # גרסת Python
├── .env.example           # תבנית למשתני סביבה
├── .gitignore            # קבצים להתעלמות ב-Git
├── engine/                # ליבת המערכת
│   ├── __init__.py
│   └── app.py            # Flask app + טעינה דינמית
├── plugins/               # תיקיית פלאגינים
│   ├── __init__.py
│   ├── hello_world.py    # פלאגין לדוגמה
│   └── users_stats.py    # פלאגין נוסף (מבואר)
└── templates/             # תבניות HTML
    └── index.html        # דשבורד ראשי
```

## 🎯 תכונות

- ✅ **מודולרי לחלוטין** - הוסף/הסר פלאגינים ללא שינוי הליבה
- ✅ **טעינה דינמית** - פלאגינים נטענים בזמן ריצה
- ✅ **עיצוב מודרני** - ממשק כהה ומקצועי
- ✅ **Bootstrap Icons** - אייקונים מובנים
- ✅ **Responsive** - תומך בכל הגדלי מסך
- ✅ **RTL Support** - תמיכה מלאה בעברית

## 🚀 התקנה והפעלה

### אפשרות 1: הרצה מקומית

#### 1. התקן את התלויות

```bash
pip install -r requirements.txt
```

#### 2. הפעל את השרת

```bash
python run.py
```

#### 3. פתח בדפדפן

```
http://localhost:5000
```

### אפשרות 2: פריסה ב-Render.com ☁️

#### שלב 1: העלה ל-GitHub

1. צור repository חדש ב-GitHub
2. העלה את כל הקבצים מהפרויקט

```bash
git init
git add .
git commit -m "Initial commit - Modular Bot V2"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

#### שלב 2: חיבור ל-Render.com

1. היכנס ל-[Render.com](https://render.com)
2. לחץ על **New +** → **Web Service**
3. חבר את ה-GitHub repository שלך
4. הגדר את הפרטים:
   - **Name**: `modular-bot-v2` (או כל שם שתרצה)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn engine.app:app`
   - **Plan**: בחר ב-`Free`

5. לחץ על **Create Web Service**

#### שלב 3: המתן לפריסה

Render יבנה ויפעיל את האפליקציה אוטומטית. תקבל URL כמו:
```
https://modular-bot-v2.onrender.com
```

#### שימוש ב-render.yaml (אוטומציה מלאה)

אם רוצה deployment אוטומטי, Render יזהה את קובץ `render.yaml` ויבנה הכל אוטומטית!

#### הערות חשובות ל-Render:

- ⚠️ **Free tier** - השרת ייכבה אחרי 15 דקות חוסר פעילות
- 🔄 **Cold start** - טעינה ראשונה יכולה לקחת 30-60 שניות
- 🌍 **HTTPS** - Render נותן HTTPS חינם אוטומטית
- 📊 **Logs** - ניתן לראות לוגים בממשק של Render

## 🔌 יצירת פלאגין חדש

### שלב 1: צור קובץ פלאגין חדש

צור קובץ חדש בתיקיית `plugins/`, למשל: `my_plugin.py`

```python
"""
My Plugin - תיאור הפלאגין
"""

def get_dashboard_widget():
    """
    מחזיר ווידג'ט לדשבורד
    
    Returns:
        dict: מילון עם הפרמטרים הבאים:
            - title: כותרת הווידג'ט
            - value: הערך המרכזי להצגה
            - label: תווית משנה
            - status: success/warning/danger/info
            - icon: Bootstrap Icon class (למשל: bi-heart)
    """
    return {
        'title': 'My Custom Widget',
        'value': '42',
        'label': 'Active Users',
        'status': 'success',
        'icon': 'bi-people'
    }
```

### שלב 2: הפעל את הפלאגין

ערוך את `config.py` והוסף את הפלאגין לרשימה:

```python
ENABLED_PLUGINS = [
    "hello_world",
    "my_plugin",  # ← הוסף כאן
]
```

### שלב 3: הפעל מחדש את השרת

```bash
python run.py
```

## 🎨 סטטוסים זמינים

| Status    | צבע      | שימוש                    |
|-----------|---------|--------------------------|
| `success` | 🟢 ירוק | מערכת תקינה, הצלחה       |
| `warning` | 🟡 צהוב | אזהרה, שים לב            |
| `danger`  | 🔴 אדום | שגיאה, בעיה קריטית       |
| `info`    | 🔵 כחול | מידע כללי                |

## 🎭 אייקונים מומלצים (Bootstrap Icons)

- `bi-cpu` - מעבד / מערכת
- `bi-activity` - ביצועים
- `bi-people` - משתמשים
- `bi-heart-pulse` - בריאות מערכת
- `bi-database` - מסד נתונים
- `bi-lightning` - מהירות
- `bi-shield-check` - אבטחה
- `bi-graph-up` - סטטיסטיקות

[רשימה מלאה של אייקונים](https://icons.getbootstrap.com/)

## 📊 דוגמאות לווידג'טים

### סטטוס מערכת

```python
def get_dashboard_widget():
    return {
        'title': 'System Health',
        'value': '98%',
        'label': 'All systems operational',
        'status': 'success',
        'icon': 'bi-heart-pulse'
    }
```

### משתמשים פעילים

```python
def get_dashboard_widget():
    return {
        'title': 'Active Users',
        'value': '1,234',
        'label': 'Online now',
        'status': 'info',
        'icon': 'bi-people'
    }
```

### אזהרת זיכרון

```python
def get_dashboard_widget():
    return {
        'title': 'Memory Usage',
        'value': '87%',
        'label': 'Approaching limit',
        'status': 'warning',
        'icon': 'bi-cpu'
    }
```

## 🛠️ התאמה אישית

### קבצי הגדרה

#### `config.py`
קובץ ההגדרות המרכזי של הפרויקט.

#### `.env` (אופציונלי)
משתני סביבה מקומיים. העתק את `.env.example` ל-`.env` והתאם:
```bash
cp .env.example .env
```

#### `Procfile`
הגדרת command ל-Render/Heroku - כבר מוגדר ל-gunicorn.

#### `render.yaml`
הגדרות deployment אוטומטי ל-Render.com.

### שינוי פורט

ערוך `config.py`:

```python
PORT = 8080  # במקום 5000
```

### שינוי שם הבוט

```python
BOT_NAME = "My Awesome Dashboard"
```

### מצב Debug

```python
DEBUG = False  # לסביבת ייצור
```

## 📝 טיפים

1. **פלאגינים עצמאיים** - כל פלאגין לא צריך לדעת על פלאגינים אחרים
2. **פונקציה אחת** - כל פלאגין חייב להכיל `get_dashboard_widget()`
3. **מילון פשוט** - החזר מילון עם 5 השדות הנדרשים
4. **שמות ייחודיים** - תן שם ייחודי לכל פלאגין

## 🔐 אבטחה

### משתני סביבה

הפרויקט תומך במשתני סביבה דרך קובץ `.env` או דרך הגדרות הפלטפורמה (Render).

משתנים נתמכים:
- `PORT` - פורט השרת (Render מגדיר אוטומטית)
- `DEBUG` - מצב debug (False בייצור)

### הגדרות אבטחה

- לא להריץ בפרודקשן עם `DEBUG=True`
- להשתמש ב-HTTPS בסביבת ייצור
- להגביל גישה לשרת לפי צורך

## 📄 רישיון

MIT License - חופשי לשימוש ושינוי.

## 💡 תמיכה

נוצר על ידי אמיר חיים | 2025
