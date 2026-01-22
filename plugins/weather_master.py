# מזג האוויר בתל אביב 🌤️

אני לא יכול לגשת ישירות ל-API של wttr.in בזמן אמת, אבל אני יכול להראות לך כיצד לעשות זאת!

## דרכים לקבל את מזג האוויר:

### 1️⃣ דרך הדפדפן:
```
https://wttr.in/Tel_Aviv?lang=he
```

### 2️⃣ דרך שורת הפקודה (Terminal):
```bash
curl wttr.in/Tel_Aviv?lang=he
```

### 3️⃣ גרסה קצרה:
```bash
curl wttr.in/Tel_Aviv?format=3
```

### 4️⃣ בפייתון:
```python
import requests

response = requests.get('https://wttr.in/Tel_Aviv?format=j1')
data = response.json()

current = data['current_condition'][0]
print(f"🌡️ טמפרטורה: {current['temp_C']}°C")
print(f"☁️ מזג אוויר: {current['weatherDesc'][0]['value']}")
print(f"💨 רוח: {current['windspeedKmph']} קמ״ש")
print(f"💧 לחות: {current['humidity']}%")
```

### 5️⃣ פקודה /weather לבוט טלגרם/דיסקורד:
```python
async def weather_command(city="Tel_Aviv"):
    url = f"https://wttr.in/{city}?format=%l:+%c+%t+%w+%h"
    response = requests.get(url)
    return response.text
```

**רוצה שאכתוב לך קוד מלא לבוט מסוים? ספר לי באיזו פלטפורמה! 🤖**