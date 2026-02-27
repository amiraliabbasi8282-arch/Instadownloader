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
    await update.message.reply_text('📥 ربات آماده است! لینک پینترست، اسپاتیفای، تیک‌تاک یا اینستاگرام بفرست.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): return

    status_msg = await update.message.reply_text('⏳ در حال دور زدن محدودیت‌ها و دانلود...')
    ffmpeg_path = get_ffmpeg_path()

    # تنظیمات بسیار سخت‌گیرانه برای فریب دادن سایت‌ها
    ydl_opts_base = {
        'outtmpl': 'dl_file.%(ext)s',
        'quiet': True,
        'no_warnings': False, # هشدارها را فعال کردیم تا در لاگ ببینیم چه می‌شود
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    }
    if ffmpeg_path: ydl_opts_base['ffmpeg_location'] = ffmpeg_path

    is_spotify = "spotify" in url
    is_pinterest = "pinterest" in url or "pin.it" in url
    
    # اولویت‌بندی جستجو
    priorities = []
    if is_spotify:
        priorities = [
            {"name": "YouTube Music Search", "query": f"ytsearch1:{url}", "opts": {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]}},
            {"name": "SoundCloud Search", "query": f"scsearch1:{url}", "opts": {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]}}
        ]
    elif is_pinterest:
        # برای پینترست مستقیماً تلاش می‌کنیم
        priorities = [{"name": "Pinterest Engine", "query": url, "opts": {'format': 'best'}}]
    else:
        priorities = [{"name": "General Engine", "query": url, "opts": {'format': 'best'}}]

    success = False
    last_error = ""

    for step in priorities:
        try:
            await status_msg.edit_text(f'🔍 منبع: {step["name"]}...')
            opts = ydl_opts_base.copy()
            opts.update(step["opts"])

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(step["query"], download=True)
                if 'entries' in info: info = info['entries'][0]
                filename = ydl.prepare_filename(info)
                
                if is_spotify:
                    filename = filename.rsplit('.', 1)[0] + '.mp3'

                if os.path.exists(filename):
                    if is_spotify:
                        await update.message.reply_audio(audio=open(filename, 'rb'), caption="🎵 منبع کمکی اسپاتیفای")
                    else:
                        await update.message.reply_video(video=open(filename, 'rb'), caption="✅ دانلود شد")
                    os.remove(filename)
                    success = True
                    break
        except Exception as e:
            last_error = str(e)
            continue

    if success:
        await status_msg.delete()
    else:
        # نمایش دلیل دقیق ارور برای عیب‌یابی
        if "403" in last_error:
            msg = "❌ خطای ۴۰۳: سرور اجازه دسترسی نمی‌دهد (آی‌پی بلاک است)."
        elif "404" in last_error:
            msg = "❌ خطای ۴۰۴: محتوا پیدا نشد یا لینک خصوصی است."
        else:
            msg = f"❌ خطا: {last_error[:100]}"
        await status_msg.edit_text(msg)

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
