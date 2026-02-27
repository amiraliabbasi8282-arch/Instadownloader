import os
import re
import shutil
import instaloader
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# دریافت توکن از متغیرهای محیطی Railway
TOKEN = os.getenv('BOT_TOKEN')

# تنظیمات اینستالودر
L = instaloader.Instaloader()
L.save_metadata = False  # برای جلوگیری از دانلود فایل‌های متنی اضافه
L.download_comments = False

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'سلام! به ربات دانلودر خوش آمدید. 🖐\n\n'
        'فقط کافیه لینک پست یا Reels رو برای من بفرستی تا فایلش رو برات بفرستم.'
    )

# پردازش لینک و دانلود
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    
    if "instagram.com" not in url:
        await update.message.reply_text('❌ لطفاً یک لینک معتبر از اینستاگرام بفرستید.')
        return

    status_msg = await update.message.reply_text('⏳ در حال بررسی لینک و استخراج ویدیو...')

    try:
        # استخراج Shortcode با استفاده از Regex (هوشمند برای انواع لینک‌ها)
        match = re.search(r"/(?:p|reels|reel|tv)/([A-Za-z0-9_-]+)", url)
        
        if not match:
            await status_msg.edit_text("❌ متأسفانه نتونستم کد پست رو از این لینک تشخیص بدم. مطمئن شو که لینک رو درست کپی کردی.")
            return
            
        shortcode = match.group(1)
        
        # ایجاد یک پوشه موقت برای دانلود
        download_path = f"dl_{shortcode}"
        if not os.path.exists(download_path):
            os.makedirs(download_path)

        # دانلود محتوا
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=download_path)

        # ارسال فایل‌های دانلود شده
        files = sorted(os.listdir(download_path))
        found_content = False

        for file in files:
            file_full_path = os.path.join(download_path, file)
            
            if file.endswith('.mp4'):
                with open(file_full_path, 'rb') as video:
                    await update.message.reply_video(video=video, caption=f"✅ پست با کد {shortcode} دانلود شد.")
                found_content = True
            elif file.endswith('.jpg'):
                # ارسال عکس فقط اگر ویدیو همراهش نباشد (برای جلوگیری از ارسال تکراری کاور ویدیو)
                if not any(f.endswith('.mp4') for f in files):
                    with open(file_full_path, 'rb') as photo:
                        await update.message.reply_photo(photo=photo)
                    found_content = True

        if not found_content:
            await status_msg.edit_text("❌ فایلی برای ارسال پیدا نشد. ممکنه پست حذف شده باشه یا خصوصی باشه.")
        else:
            await status_msg.delete()

        # پاکسازی پوشه دانلود
        shutil.rmtree(download_path)

    except Exception as e:
        print(f"Error: {e}")
        error_text = str(e)
        if "401" in error_text or "Login required" in error_text:
            await status_msg.edit_text('❌ اینستاگرام اجازه دسترسی نداد. (احتمالاً پیج خصوصیه یا آی‌پی سرور محدود شده)')
        else:
            await status_msg.edit_text('❌ خطای غیرمنتظره‌ای رخ داد. لطفاً دوباره تلاش کنید.')

# اجرای اصلی ربات
if __name__ == '__main__':
    if not TOKEN:
        print("Error: BOT_TOKEN variable is not set in Railway!")
    else:
        app = Application.builder().token(TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("Bot is up and running...")
        app.run_polling()
