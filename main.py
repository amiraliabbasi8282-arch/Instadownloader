import os
import re
import shutil
import yt_dlp
import instaloader
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- تنظیمات متغیرها از Railway ---
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
    for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/nix/var/nix/profiles/default/bin/ffmpeg']:
        if os.path.exists(path): return path
    try:
        return subprocess.check_output(['which', 'ffmpeg']).decode('utf-8').strip()
    except: return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('سلام! لینک اینستاگرام، تیک‌تاک، پینترست یا اسپاتیفای بفرست تا برات دانلود کنم. 📥')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): return

    status_msg = await update.message.reply_text('⏳ در حال بررسی لینک و تلاش برای دانلود...')
    ffmpeg_path = get_ffmpeg_path()

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

    # ۲. بخش چندرسانه‌ای (Spotify, Pinterest, TikTok)
    else:
        ydl_opts_base = {
            'outtmpl': 'dl_file.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        if ffmpeg_path: ydl_opts_base['ffmpeg_location'] = ffmpeg_path

        # تعیین استراتژی اولویت‌بندی
        is_spotify = "spotify" in url
        if is_spotify:
            priorities = [
                {"name": "Spotify Direct", "query": url, "opts": {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]}},
                {"name": "YouTube Music", "query": f"ytsearch1:{url}", "opts": {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]}},
                {"name": "SoundCloud", "query": f"scsearch1:{url}", "opts": {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]}}
            ]
        elif "pinterest" in url or "pin.it" in url:
            priorities = [{"name": "Pinterest", "query": url, "opts": {'format': 'best', 'referer': 'https://www.pinterest.com/'}}]
        else:
            priorities = [{"name": "Media Downloader", "query": url, "opts": {'format': 'best'}}]

        success = False
        for step in priorities:
            try:
                await status_msg.edit_text(f'⏳ تلاش از منبع: {step["name"]}...')
                opts = ydl_opts_base.copy()
                opts.update(step["opts"])

                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(step["query"], download=True)
                    if 'entries' in info: info = info['entries'][0]
                    filename = ydl.prepare_filename(info)
                    if is_spotify: filename = filename.rsplit('.', 1)[0] + '.mp3'

                    if os.path.exists(filename):
                        if is_spotify:
                            await update.message.reply_audio(audio=open(filename, 'rb'), caption=f"🎵 {step['name']}")
                        else:
                            await update.message.reply_video(video=open(filename, 'rb'), caption=f"✅ {step['name']}")
                        os.remove(filename)
                        success = True
                        break
            except: continue

        if success:
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ متأسفانه محتوا یافت نشد یا در تمام منابع مسدود شده است.")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 Bot is running with Pinterest & Multi-Source Spotify...")
    app.run_polling(drop_pending_updates=True)
