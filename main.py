import os
import re
import shutil
import yt_dlp
import instaloader
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv('BOT_TOKEN')

def get_ffmpeg_path():
    for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/nix/var/nix/profiles/default/bin/ffmpeg']:
        if os.path.exists(path): return path
    try:
        return subprocess.check_output(['which', 'ffmpeg']).decode('utf-8').strip()
    except: return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('📥 آماده‌ام! لینک رو بفرست.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): return

    status_msg = await update.message.reply_text('⏳ در حال تلاش برای استخراج فایل...')
    ffmpeg_path = get_ffmpeg_path()

    # تنظیمات بسیار منعطف برای دور زدن مسدودیت
    ydl_opts = {
        'outtmpl': 'dl_file.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'format': 'best', # انتخاب ساده‌ترین فرمت موجود برای جلوگیری از ارور Format Not Available
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
        'socket_timeout': 30,
    }
    
    if ffmpeg_path: ydl_opts['ffmpeg_location'] = ffmpeg_path

    is_spotify = "spotify" in url
    is_pinterest = "pinterest" in url or "pin.it" in url

    # استراتژی نهایی
    query = f"ytsearch1:{url}" if is_spotify else url
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # تلاش برای دریافت اطلاعات بدون دانلود اولیه
            info = ydl.extract_info(query, download=True)
            if 'entries' in info: info = info['entries'][0]
            
            filename = ydl.prepare_filename(info)
            # اگر فرمت خروجی تغییر کرده بود (مثلاً m4a به mp3)
            if is_spotify or not os.path.exists(filename):
                potential_file = filename.rsplit('.', 1)[0] + '.mp3'
                if os.path.exists(potential_file): filename = potential_file

            if os.path.exists(filename):
                if is_spotify:
                    await update.message.reply_audio(audio=open(filename, 'rb'), caption="🎵 تقدیم شما")
                else:
                    await update.message.reply_video(video=open(filename, 'rb'), caption="✅ دانلود شد")
                os.remove(filename)
                await status_msg.delete()
                return
            
    except Exception as e:
        error_str = str(e)
        if "403" in error_str or "Forbidden" in error_str:
            await status_msg.edit_text("❌ سرور سایت مبدأ اجازه دانلود به آی‌پی ربات رو نمیده (ارور 403).")
        else:
            await status_msg.edit_text(f"❌ خطا در پردازش: {error_str[:100]}")
        return

    await status_msg.edit_text("❌ فایل دانلود شد اما پیدا نشد! احتمالاً مشکل در FFmpeg سرور هست.")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).read_timeout(60).write_timeout(60).connect_timeout(60).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
