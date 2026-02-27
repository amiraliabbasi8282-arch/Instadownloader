import os
import instaloader
import shutil
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# دریافت توکن از متغیرهای محیطی Railway (امنیت بالا)
TOKEN = os.getenv('BOT_TOKEN')

# تنظیمات اینستالودر
L = instaloader.Instaloader()

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'سلام! خوش آمدید. 🖐\n'
        'لطفاً لینک پست اینستاگرام مورد نظرتون رو بفرستید تا براتون دانلود کنم.'
    )

# پردازش لینک و دانلود
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    
    # بررسی معتبر بودن لینک
    if "instagram.com" not in url:
        await update.message.reply_text('❌ لطفاً یک لینک معتبر از اینستاگرام بفرستید.')
        return

    status_msg = await update.message.reply_text('⏳ در حال بررسی و دانلود... لطفاً کمی صبر کنید.')

    try:
        # استخراج کد کوتاه پست (Shortcode) از لینک
        # لینک‌ها معمولاً به این شکل هستند: instagram.com/p/SHORTCODE/
        parts = url.split("/")
        shortcode = parts[parts.index("p") + 1] if "p" in parts else parts[parts.index("reels") + 1] if "reels" in parts else None

        if not shortcode:
            await status_msg.edit_text("❌ نتونستم کد پست رو از لینک تشخیص بدم.")
            return

        # دانلود پست در یک پوشه با نام همان کد
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=shortcode)

        # گشتن دنبال فایل‌های دانلود شده و ارسال آن‌ها
        files = os.listdir(shortcode)
        for file in files:
            file_path = f"{shortcode}/{file}"
            
            if file.endswith('.mp4'):
                await update.message.reply_video(video=open(file_path, 'rb'), caption="خدمت شما! ✅")
            elif file.endswith('.jpg'):
                await update.message.reply_photo(photo=open(file_path, 'rb'))

        # پاک کردن فایل‌ها از حافظه سرور Railway بعد از ارسال
        shutil.rmtree(shortcode)
        await status_msg.delete()

    except Exception as e:
        print(f"Error: {e}")
        await status_msg.edit_text(f'❌ متأسفانه خطایی رخ داد. ممکنه پست خصوصی (Private) باشه یا اینستاگرام دسترسی رو محدود کرده باشه.')

# اجرای ربات
if __name__ == '__main__':
    if not TOKEN:
        print("خطا: مقدار BOT_TOKEN در Railway تنظیم نشده است!")
    else:
        app = Application.builder().token(TOKEN).build()
        
        # اضافه کردن هندلرها
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("Bot is running...")
        app.run_polling()
