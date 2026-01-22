```python
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """פונקציה שמגיבה לפקודת /start"""
    await update.message.reply_text(
        "שלום! אני בוט שסופר מילים.\n"
        "שלח לי הודעה ואני אספור כמה מילים יש בה."
    )

async def count_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """פונקציה שסופרת מילים בהודעה"""
    message_text = update.message.text
    
    # ספירת מילים (מפריד לפי רווחים)
    words = message_text.split()
    word_count = len(words)
    
    # שליחת תשובה
    await update.message.reply_text(f"שלחת הודעה עם {word_count} מילים")

def main():
    """פונקציה ראשית שמריצה את הבוט"""
    
    # הכנס כאן את הטוקן של הבוט שלך מ-BotFather
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    # יצירת האפליקציה
    application = Application.builder().token(TOKEN).build()
    
    # הוספת handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, count_words))
    
    # הרצת הבוט
    print("הבוט רץ...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
```

**הוראות התקנה והפעלה:**

1. **התקן את הספרייה הנדרשת:**
```bash
pip install python-telegram-bot
```

2. **צור בוט חדש:**
   - פתח את Telegram וחפש את @BotFather
   - שלח `/newbot`
   - עקוב אחרי ההוראות ותקבל טוקן

3. **הכנס את הטוקן:**
   - החלף את `YOUR_BOT_TOKEN_HERE` בטוקן שקיבלת

4. **הרץ את הבוט:**
```bash
python bot.py
```

5. **התחל לשלוח הודעות לבוט שלך בטלגרם!**

הבוט יספור את כל המילים בכל הודעה שתשלח ויגיב בעברית 😊