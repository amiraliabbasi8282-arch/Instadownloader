import os
import re
import shutil
import yt_dlp
import instaloader
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# --- تنظیمات متغیرها ---
TOKEN = os.getenv('BOT_TOKEN')

def get_ffmpeg_path():
    for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/nix/var/nix/profiles/default/bin/ffmpeg']:
        if os.path.exists(path): return path
    try:
        return subprocess.check_output(['which', 'ffmpeg']).decode('utf-8').strip()
    except: return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('📥 لینک ویدیو (یوتیوب، اینستا، پینترست و...) رو بفرست برات دانلود کنم!')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): return

    # تشخیص لینک یوتیوب
    if "youtube.com" in url or "youtu.be" in url:
        keyboard = [
            [
                InlineKeyboardButton("🎬 ویدیو (Video)", callback_data=f"yt_video|{url}"),
                InlineKeyboardButton("🎵 آهنگ (Audio)", callback_data=f"yt_audio|{url}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("چطوری بفرستمش؟ یکی رو انتخاب کن:", reply_markup=reply_markup)
        return

    # بقیه منابع (اینستا، پینترست و غیره) مطابق کدهای قبلی
    status_msg = await update.message.reply_text('⏳ در حال پردازش...')
    # ... (کدهای قبلی برای اینستاگرام و پینترست اینجا قرار می‌گیرد)

async def youtube_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("|")
    mode = data[0] # yt_video یا yt_audio
    url = data[1]
    
    status_msg = await query.edit_message_text(text="⏳ در حال استخراج و دانلود از یوتیوب...")
    ffmpeg_path = get_ffmpeg_path()
    
    ydl_opts = {
        'outtmpl': 'yt_download.%(ext)s',
        'quiet': True,
    }
    if ffmpeg_path: ydl_opts['ffmpeg_location'] = ffmpeg_path

    if mode == "yt_audio":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'})

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if mode == "yt_audio": filename = filename.rsplit('.', 1)[0] + '.mp3'

            if os.path.exists(filename):
                if mode == "yt_audio":
                    await query.message.reply_audio(audio=open(filename, 'rb'), caption="🎵 موزیک استخراج شده")
                else:
                    await query.message.reply_video(video=open(filename, 'rb'), caption="✅ ویدیوی یوتیوب")
                os.remove(filename)
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ فایل نهایی ساخته نشد.")
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در یوتیوب: {str(e)[:100]}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # هندلر برای مدیریت کلیک دکمه‌ها
    app.add_handler(CallbackQueryHandler(youtube_callback, pattern="^yt_"))
    
    print("🚀 ربات یوتیوب‌درایور روشن شد...")
    app.run_polling(drop_pending_updates=True)
