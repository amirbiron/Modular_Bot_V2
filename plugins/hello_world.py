"""
Hello World Plugin - פלאגין לדוגמה
מציג סטטוס מערכת בסיסי בדשבורד
"""


def get_dashboard_widget():
    """
    מחזיר ווידג'ט לדשבורד
    
    Returns:
        dict: מילון עם פרטי הווידג'ט
            - title: כותרת הווידג'ט
            - value: הערך המרכזי להצגה
            - label: תווית משנה
            - status: success/warning/danger/info
            - icon: Bootstrap Icon class name
    """
    return {
        'title': 'System Status',
        'value': 'Online',
        'label': 'All systems normal',
        'status': 'success',
        'icon': 'bi-cpu'
    }


# ניתן להוסיף פונקציות נוספות לצורך פנימי
def _internal_check():
    """פונקציה פנימית לדוגמה - לא תיקרא מהמנוע"""
    return True
