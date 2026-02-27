import os
import re
import shutil
import yt_dlp
import instaloader
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- تنظیمات متغیرها ---
TOKEN = os.getenv('BOT_TOKEN')
INSTA_USER = os.getenv('INSTA_USER')
INSTA_PASS = os.getenv('INSTA_PASS')

# تنظیمات اینستاگرام
L = instaloader.Instaloader()
if INSTA_USER and INSTA_PASS:
    try:
        L.login(INSTA_USER, INSTA_PASS)
        print("✅ Instagram logged in!")
    except Exception as e:
        print(f"⚠️ Instagram Login Failed: {e}")

# تابع پیدا کردن مسیر FFmpeg در سرور Railway
def get_ffmpeg_path():
    try:
        # جستجو برای پیدا کردن مسیر نصب شده FFmpeg
        path = subprocess.check_output(['which', 'ffmpeg']).decode('utf-8').strip()
        return path
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('سلام! لینک اینستاگرام، تیک‌تاک یا اسپاتیفای بفرست تا برات دانلود کنم. 📥')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    status_msg = await update.message.reply_text('⏳ در حال پردازش... لطفاً صبور باشید.')

    # ۱. بخش اینستاگرام
    if "instagram.com" in url:
        try:
            match = re.search(r"/(?:p|reels|reel|tv)/([A-Za-z0-9_-]+)", url)
            shortcode = match.group(1)
            download_path = f"insta_{shortcode}"
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            L.download_post(post, target=download_path)
            
            for file in os.listdir(download_path):
                file_path = os.path.join(download_path, file)
                if file.endswith('.mp4'):
                    await update.message.reply_video(video=open(file_path, 'rb'), caption="بفرما! ✅")
                elif file.endswith('.jpg') and not any(f.endswith('.mp4') for f in os.listdir(download_path)):
                    await update.message.reply_photo(photo=open(file_path, 'rb'))
            
            shutil.rmtree(download_path)
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ خطای اینستاگرام: {str(e)[:50]}")

    # ۲. بخش اسپاتیفای و تیک‌تاک
    elif "tiktok.com" in url or "spotify.com" in url or "spotify.com" in url:
        is_spotify = "spotify" in url
        ffmpeg_path = get_ffmpeg_path()
        
        ydl_opts = {
            'outtmpl': 'downloaded_file.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }

        if is_spotify:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
            if ffmpeg_path:
                ydl_opts['ffmpeg_location'] = ffmpeg_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            ext = 'mp3' if is_spotify else 'mp4'
            final_file = f'downloaded_file.{ext}'

            # ارسال فایل به کاربر
            if os.path.exists(final_file):
                if is_spotify:
                    await update.message.reply_audio(audio=open(final_file, 'rb'), caption="آهنگ اسپاتیفای شما آماده است 🎵")
                else:
                    await update.message.reply_video(video=open(final_file, 'rb'), caption="ویدیو تیک‌تاک شما آماده است ✅")
                os.remove(final_file)
            else:
                # اگر فایل پیدا نشد اما دانلود موفق بود (تغییر نام احتمالی توسط yt-dlp)
                for f in os.listdir('.'):
                    if f.startswith('downloaded_file'):
                        await update.message.reply_document(document=open(f, 'rb'))
                        os.remove(f)

            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ خطا: FFmpeg روی سرور یافت نشد یا لینک معتبر نیست.")
            print(f"Download Error: {e}")

    else:
        await status_msg.edit_text("❌ این لینک پشتیبانی نمی‌شود.")

if __name__ == '__main__':
    if not TOKEN:
        print("❌ Error: BOT_TOKEN is not set in Variables!")
    else:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        print("🚀 Bot is running and waiting for links...")
        app.run_polling(drop_pending_updates=True)
