import os
import re
import shutil
import yt_dlp
import instaloader
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv('BOT_TOKEN')
L = instaloader.Instaloader()
L.save_metadata = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('سلام! لینک اینستاگرام یا تیک‌تاک رو بفرست تا برات دانلود کنم. 📥')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    status_msg = await update.message.reply_text('⏳ در حال پردازش لینک...')

    # --- بخش اینستاگرام ---
    if "instagram.com" in url:
        try:
            match = re.search(r"/(?:p|reels|reel|tv)/([A-Za-z0-9_-]+)", url)
            if not match:
                await status_msg.edit_text("❌ کد پست اینستاگرام تشخیص داده نشد.")
                return
            
            shortcode = match.group(1)
            download_path = f"insta_{shortcode}"
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            L.download_post(post, target=download_path)

            for file in os.listdir(download_path):
                if file.endswith('.mp4'):
                    await update.message.reply_video(video=open(f"{download_path}/{file}", 'rb'))
                elif file.endswith('.jpg') and not any(f.endswith('.mp4') for f in os.listdir(download_path)):
                    await update.message.reply_photo(photo=open(f"{download_path}/{file}", 'rb'))
            
            shutil.rmtree(download_path)
            await status_msg.delete()

        except Exception as e:
            await status_msg.edit_text(f"❌ خطای اینستاگرام: {str(e)}")

    # --- بخش تیک‌تاک ---
    elif "tiktok.com" in url:
        try:
            ydl_opts = {
                'outtmpl': 'tiktok_video.mp4',
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            await update.message.reply_video(video=open('tiktok_video.mp4', 'rb'), caption="خدمت شما از تیک‌تاک! ✅")
            os.remove('tiktok_video.mp4')
            await status_msg.delete()

        except Exception as e:
            await status_msg.edit_text("❌ خطا در دانلود از تیک‌تاک. ممکنه ویدیو حذف شده باشه یا لینک اشتباه باشه.")
            if os.path.exists('tiktok_video.mp4'): os.remove('tiktok_video.mp4')

    else:
        await status_msg.edit_text("❌ این لینک پشتیبانی نمی‌شه. فعلاً فقط اینستاگرام و تیک‌تاک!")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)
