import os
import re
import shutil
import yt_dlp
import instaloader
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# --- تنظیمات متغیرها (از پنل Railway دریافت می‌شوند) ---
TOKEN = os.getenv('BOT_TOKEN')
INSTA_USER = os.getenv('INSTA_USER')
INSTA_PASS = os.getenv('INSTA_PASS')

# تابع پیدا کردن مسیر FFmpeg در سرور
def get_ffmpeg_path():
    for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/nix/var/nix/profiles/default/bin/ffmpeg']:
        if os.path.exists(path): return path
    try:
        return subprocess.check_output(['which', 'ffmpeg']).decode('utf-8').strip()
    except: return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🚀 ربات همه‌کاره دانلودر فعال شد!\n\nلینک یوتیوب، اینستاگرام، تیک‌تاک، پینترست، اسپاتیفای یا ساوندکلود را بفرست تا برات دانلود کنم.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): return

    # ۱. مدیریت اختصاصی یوتیوب (انتخاب کیفیت/آهنگ)
    if "youtube.com" in url or "youtu.be" in url:
        keyboard = [
            [InlineKeyboardButton("🎬 انتخاب کیفیت ویدیو", callback_data=f"yt_list|{url}")],
            [InlineKeyboardButton("🎵 آهنگ (MP3 + کاور + تگ)", callback_data=f"yt_audio|{url}")]
        ]
        await update.message.reply_text("چه فرمتی از یوتیوب مد نظرت هست؟", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ۲. پردازش سایر منابع
    status_msg = await update.message.reply_text('⏳ در حال پردازش لینک...')
    ffmpeg_path = get_ffmpeg_path()

    # بخش اینستاگرام
    if "instagram.com" in url:
        try:
            match = re.search(r"/(?:p|reels|reel|tv)/([A-Za-z0-9_-]+)", url)
            if not match: return await status_msg.edit_text("❌ لینک اینستاگرام معتبر نیست.")
            shortcode = match.group(1)
            L = instaloader.Instaloader()
            if INSTA_USER and INSTA_PASS: L.login(INSTA_USER, INSTA_PASS)
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            target = f"insta_{shortcode}"
            L.download_post(post, target=target)
            for f in os.listdir(target):
                p = os.path.join(target, f)
                if f.endswith('.mp4'): await update.message.reply_video(video=open(p, 'rb'))
                elif f.endswith('.jpg') and not any(x.endswith('.mp4') for x in os.listdir(target)):
                    await update.message.reply_photo(photo=open(p, 'rb'))
            shutil.rmtree(target)
            await status_msg.delete()
        except Exception as e: await status_msg.edit_text(f"❌ خطای اینستاگرام: {str(e)[:50]}")

    # بخش تیک‌تاک، پینترست، اسپاتیفای و ساوندکلود
    else:
        is_spotify = "spotify" in url
        ydl_opts = {
            'outtmpl': 'file_%(title)s.%(ext)s',
            'quiet': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
        if ffmpeg_path: ydl_opts['ffmpeg_location'] = ffmpeg_path

        queries = [{"n": "Direct", "q": url, "o": {'format': 'best'}}]
        if is_spotify:
            queries = [
                {"n": "YouTube Music", "q": f"ytsearch1:{url}", "o": {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]}},
                {"n": "SoundCloud", "q": f"scsearch1:{url}", "o": {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]}}
            ]

        success = False
        for q in queries:
            try:
                opts = {**ydl_opts, **q['o']}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(q['q'], download=True)
                    fname = ydl.prepare_filename(info if 'entries' not in info else info['entries'][0])
                    if is_spotify: fname = fname.rsplit('.', 1)[0] + '.mp3'
                    if os.path.exists(fname):
                        if is_spotify: await update.message.reply_audio(audio=open(fname, 'rb'), title=info.get('title'))
                        else: await update.message.reply_video(video=open(fname, 'rb'))
                        os.remove(fname)
                        success = True; break
            except: continue
        if not success: await status_msg.edit_text("❌ خطا: محتوا یافت نشد یا مسدود شده است.")
        else: await status_msg.delete()

async def yt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    action, url = data[0], data[1]
    ffmpeg_path = get_ffmpeg_path()

    # لیست کردن کیفیت‌ها
    if action == "yt_list":
        await query.edit_message_text("🔍 در حال بررسی کیفیت‌های موجود...")
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            res_list = sorted(list(set(f.get('height') for f in formats if f.get('height') and f.get('height') <= 1080)), reverse=True)
            btns = [[InlineKeyboardButton(f"🎬 {r}p", callback_data=f"yt_dl|{url}|{r}")] for r in res_list[:5]]
            if not btns: return await query.edit_message_text("❌ کیفیتی یافت نشد.")
            await query.edit_message_text("کیفیت مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(btns))

    # دانلود ویدیو یوتیوب
    elif action == "yt_dl":
        res = data[2]
        await query.edit_message_text(f"⏳ در حال دانلود با کیفیت {res}p...")
        opts = {
            'format': f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res}]',
            'outtmpl': 'yt_v.mp4', 'ffmpeg_location': ffmpeg_path, 'merge_output_format': 'mp4'
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
                await query.message.reply_video(video=open('yt_v.mp4', 'rb'), caption=f"✅ کیفیت {res}p")
                os.remove('yt_v.mp4')
                await query.message.delete()
        except Exception as e: await query.edit_message_text(f"❌ خطا: {str(e)[:50]}")

    # دانلود آهنگ یوتیوب (با کاور و تگ)
    elif action == "yt_audio":
        await query.edit_message_text("⏳ در حال استخراج آهنگ با متادیتا و کاور...")
        opts = {
            'format': 'bestaudio/best', 'outtmpl': 'music.%(ext)s', 'writethumbnail': True, 'ffmpeg_location': ffmpeg_path,
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}, {'key': 'FFmpegMetadata'}, {'key': 'EmbedThumbnail'}]
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                await query.message.reply_audio(audio=open('music.mp3', 'rb'), title=info.get('title'), performer=info.get('uploader'))
                os.remove('music.mp3')
                await query.message.delete()
        except Exception as e: await query.edit_message_text(f"❌ خطا: {str(e)[:50]}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(yt_callback, pattern="^yt_"))
    app.run_polling(drop_pending_updates=True)
