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

# تابع پیدا کردن مسیر FFmpeg
def get_ffmpeg_path():
    for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg']:
        if os.path.exists(path): return path
    try:
        return subprocess.check_output(['which', 'ffmpeg']).decode('utf-8').strip()
    except: return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('سلام! لینک اسپاتیفای بفرست تا از منابع مختلف (یوتیوب/ساوندکلود) برات پیداش کنم. 📥')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "spotify" not in url:
        await update.message.reply_text("❌ لطفاً فعلاً فقط لینک اسپاتیفای بفرستید.")
        return

    status_msg = await update.message.reply_text('⏳ در حال جستجو در یوتیوب و ساوندکلود...')
    ffmpeg_path = get_ffmpeg_path()

    # تنظیمات پایه دانلود
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'music_file.%(ext)s',
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    if ffmpeg_path: ydl_opts['ffmpeg_location'] = ffmpeg_path

    # استراتژی جستجو: اول یوتیوب، اگر نشد ساوندکلود
    search_queries = [f"ytsearch1:{url}", f"scsearch1:{url}"]
    success = False

    for query in search_queries:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(query, download=True)
                
                if 'entries' in info_dict and len(info_dict['entries']) > 0:
                    info = info_dict['entries'][0]
                    filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
                    
                    if os.path.exists(filename):
                        source = "YouTube Music" if "ytsearch" in query else "SoundCloud"
                        await update.message.reply_audio(
                            audio=open(filename, 'rb'), 
                            caption=f"🎵 پیدا شده در: {source}"
                        )
                        os.remove(filename)
                        success = True
                        break # اگر پیدا شد، جستجوی دوم را انجام نده
        except Exception as e:
            print(f"Error searching with {query}: {e}")
            continue

    if success:
        await status_msg.delete()
    else:
        await status_msg.edit_text("❌ متأسفانه آهنگ نه در یوتیوب و نه در ساوندکلود پیدا نشد.")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 ربات با قابلیت جستجوی دوگانه روشن شد...")
    app.run_polling(drop_pending_updates=True)
