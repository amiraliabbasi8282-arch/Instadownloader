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

# تابع هوشمند برای پیدا کردن مسیر FFmpeg در لینوکس (Railway)
def get_ffmpeg_path():
    for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg']:
        if os.path.exists(path):
            return path
    try:
        return subprocess.check_output(['which', 'ffmpeg']).decode('utf-8').strip()
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('سلام! لینک اینستاگرام، تیک‌تاک یا اسپاتیفای بفرست تا برات دانلود کنم. 📥')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"):
        return

    status_msg = await update.message.reply_text('⏳ در حال پردازش و دانلود...')

    # ۱. بخش اینستاگرام
    if "instagram.com" in url:
        try:
            match = re.search(r"/(?:p|reels|reel|tv)/([A-Za-z0-9_-]+)", url)
            if not match:
                await status_msg.edit_text("❌ لینک اینستاگرام معتبر نیست.")
                return
            
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
    elif "tiktok.com" in url or "spotify" in url:
        is_spotify = "spotify" in url
        ffmpeg_path = get_ffmpeg_path()
        
        ydl_opts = {
            'outtmpl': 'dl_%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }

        if is_spotify:
            # حل مشکل DRM با جستجو در یوتیوب
            ydl_opts.update({
                'format': 'bestaudio/best',
                'default_search': 'ytsearch',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
            search_url = f"ytsearch1:{url}"
        else:
            search_url = url

        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_url, download=True)
                # در حالت جستجو، اطلاعات در entries است
                if is_spotify:
                    info = info['entries'][0]
                
                filename = ydl.prepare_filename(info)
                if is_spotify:
                    filename = filename.rsplit('.', 1)[0] + '.mp3'

            if os.path.exists(filename):
                if is_spotify:
                    await update.message.reply_audio(audio=open(filename, 'rb'), caption="🎵 دانلود شده از اسپاتیفای (منبع کمکی)")
                else:
                    await update.message.reply_video(video=open(filename, 'rb'), caption="✅ دانلود شده از تیک‌تاک")
                os.remove(filename)
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ فایل دانلود شد اما یافت نشد. FFmpeg را چک کنید.")
        except Exception as e:
            await status_msg.edit_text(f"❌ خطا در دانلود: {str(e)[:100]}")
    else:
        await status_msg.edit_text("❌ این لینک پشتیبانی نمی‌شود.")

if __name__ == '__main__':
    if not TOKEN:
        print("❌ Error: BOT_TOKEN is missing!")
    else:
        # استفاده از drop_pending_updates برای حل مشکلات جزئی تداخل
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        print("🚀 Bot is running...")
        app.run_polling(drop_pending_updates=True)
