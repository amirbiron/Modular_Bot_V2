"""
Users Plugin - פלאגין לדוגמה נוסף
מציג סטטיסטיקות משתמשים

הפלאגין נטען אוטומטית כל עוד הקובץ נמצא בתיקיית plugins.
"""


def get_dashboard_widget():
    """
    מחזיר ווידג'ט עם סטטיסטיקות משתמשים
    
    Returns:
        dict: מילון עם פרטי הווידג'ט
    """
    # כאן אפשר להוסיף קוד לקריאת נתונים אמיתיים ממסד נתונים
    total_users = 1234  # לדוגמה
    
    return {
        'title': 'Total Users',
        'value': f'{total_users:,}',
        'label': 'Registered users',
        'status': 'info',
        'icon': 'bi-people'
    }


def get_user_count():
    """פונקציה עזר - לא תיקרא מהמנוע"""
    # כאן תוכל להוסיף לוגיקה לספירת משתמשים
    return 1234
