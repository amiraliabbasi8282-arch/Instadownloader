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

# تابع پیدا کردن مسیر FFmpeg (حیاتی برای رندر ویدیو و صدا)
def get_ffmpeg_path():
    for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/nix/var/nix/profiles/default/bin/ffmpeg']:
        if os.path.exists(path): return path
    try:
        return subprocess.check_output(['which', 'ffmpeg']).decode('utf-8').strip()
    except: return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('📥 ربات دانلودر فعال شد!\nلینک اینستاگرام، پینترست، تیک‌تاک یا اسپاتیفای بفرست.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): return

    status_msg = await update.message.reply_text('⏳ در حال پردازش لینک...')
    ffmpeg_path = get_ffmpeg_path()

    # تنظیمات پایه ضد-مسدودسازی
    ydl_opts_base = {
        'outtmpl': 'dl_file.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }
    if ffmpeg_path: ydl_opts_base['ffmpeg_location'] = ffmpeg_path

    # ۱. بخش اختصاصی اینستاگرام
    if "instagram.com" in url:
        try:
            shortcode = re.search(r"/(?:p|reels|reel|tv)/([A-Za-z0-9_-]+)", url).group(1)
            L = instaloader.Instaloader()
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            L.download_post(post, target=f"insta_{shortcode}")
            # ارسال فایل‌ها... (مشابه کدهای قبلی)
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ خطای اینستاگرام: {str(e)[:50]}")

    # ۲. بخش پینترست، اسپاتیفای و غیره
    else:
        is_spotify = "spotify" in url
        is_pinterest = "pinterest" in url or "pin.it" in url

        # اصلاح استراتژی برای حل ارور Format Not Available
        if is_pinterest:
            priorities = [{"name": "Pinterest Engine", "query": url, "opts": {'format': 'best'}}]
        elif is_spotify:
            priorities = [
                {"name": "YouTube Music Search", "query": f"ytsearch1:{url}", "opts": {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]}},
                {"name": "SoundCloud Search", "query": f"scsearch1:{url}", "opts": {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]}}
            ]
        else:
            priorities = [{"name": "General Engine", "query": url, "opts": {'format': 'best'}}]

        success = False
        for step in priorities:
            try:
                await status_msg.edit_text(f'🔍 تلاش برای دانلود از: {step["name"]}...')
                opts = ydl_opts_base.copy()
                opts.update(step["opts"])

                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(step["query"], download=True)
                    if 'entries' in info: info = info['entries'][0]
                    filename = ydl.prepare_filename(info)
                    if is_spotify: filename = filename.rsplit('.', 1)[0] + '.mp3'

                    if os.path.exists(filename):
                        if is_spotify:
                            await update.message.reply_audio(audio=open(filename, 'rb'))
                        else:
                            await update.message.reply_video(video=open(filename, 'rb'))
                        os.remove(filename)
                        success = True
                        break
            except Exception as e:
                print(f"Error: {e}")
                continue

        if success:
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ خطا: محتوا یافت نشد یا فرمت مورد نظر توسط سایت مسدود شده است.")

if __name__ == '__main__':
    # حل مشکل تداخل شبکه با افزایش تایم‌اوت
    app = Application.builder().token(TOKEN).read_timeout(30).write_timeout(30).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 ربات با موفقیت استارت شد.")
    app.run_polling(drop_pending_updates=True)
