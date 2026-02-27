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

# تابع پیدا کردن مسیر FFmpeg در سرور Railway
def get_ffmpeg_path():
    for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg']:
        if os.path.exists(path): return path
    try:
        return subprocess.check_output(['which', 'ffmpeg']).decode('utf-8').strip()
    except: return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('سلام! لینک اینستاگرام، تیک‌تاک، اسپاتیفای یا پینترست بفرست تا برات دانلود کنم. 📥')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" not in url: return

    status_msg = await update.message.reply_text('⏳ در حال بررسی لینک و شروع دانلود...')
    ffmpeg_path = get_ffmpeg_path()

    # ۱. بخش اختصاصی اینستاگرام (به دلیل نیاز به instaloader در برخی موارد)
    if "instagram.com" in url:
        # کد اینستاگرام که قبلاً داشتیم...
        pass 

    # ۲. بخش چندرسانه‌ای (Pinterest, TikTok, Spotify, YouTube)
    else:
        ydl_opts = {
            'outtmpl': 'dl_file.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        if ffmpeg_path: ydl_opts['ffmpeg_location'] = ffmpeg_path

        # تعیین استراتژی بر اساس نوع لینک
        if "spotify" in url:
            # اولویت‌بندی اسپاتیفای (همان سیستمی که قبلاً ساختیم)
            is_spotify = True
            search_queries = [
                {"name": "Spotify Direct", "query": url, "opts": {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]}},
                {"name": "YouTube Music", "query": f"ytsearch1:{url}", "opts": {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]}},
            ]
        elif "pinterest.com" in url or "pin.it" in url:
            is_spotify = False
            search_queries = [{"name": "Pinterest", "query": url, "opts": {'format': 'best'}}]
        else:
            # تیک‌تاک و بقیه
            is_spotify = False
            search_queries = [{"name": "Media Downloader", "query": url, "opts": {'format': 'best'}}]

        success = False
        for step in search_queries:
            try:
                await status_msg.edit_text(f'⏳ تلاش برای دانلود از: {step["name"]}...')
                current_opts = ydl_opts.copy()
                current_opts.update(step["opts"])

                with yt_dlp.YoutubeDL(current_opts) as ydl:
                    info = ydl.extract_info(step["query"], download=True)
                    if 'entries' in info: info = info['entries'][0]
                    
                    filename = ydl.prepare_filename(info)
                    # اصلاح پسوند برای فایل‌های صوتی اسپاتیفای
                    if is_spotify:
                        filename = filename.rsplit('.', 1)[0] + '.mp3'

                    if os.path.exists(filename):
                        if is_spotify:
                            await update.message.reply_audio(audio=open(filename, 'rb'), caption=f"🎵 {step['name']}")
                        else:
                            await update.message.reply_video(video=open(filename, 'rb'), caption=f"✅ {step['name']}")
                        
                        os.remove(filename)
                        success = True
                        break
            except Exception as e:
                continue

        if success:
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ متأسفانه محتوا یافت نشد یا لینک مسدود شده است.")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
