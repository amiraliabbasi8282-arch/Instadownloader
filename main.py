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
    await update.message.reply_text('سلام! لینک آهنگ رو بفرست تا به ترتیب از اسپاتیفای، یوتیوب موزیک، یوتیوب یا ساوندکلود برات پیداش کنم. 📥')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" not in url: return

    status_msg = await update.message.reply_text('⏳ در حال تلاش برای دانلود (اولویت ۱: اسپاتیفای)...')
    ffmpeg_path = get_ffmpeg_path()

    # تنظیمات پایه برای تبدیل به MP3
    ydl_opts_base = {
        'format': 'bestaudio/best',
        'outtmpl': 'music_file.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    if ffmpeg_path: ydl_opts_base['ffmpeg_location'] = ffmpeg_path

    # تعریف لیست اولویت‌ها
    # ۱. دانلود مستقیم ۲. جستجو در یوتیوب موزیک ۳. جستجو در یوتیوب ۴. جستجو در ساوندکلود
    priorities = [
        {"name": "Spotify (Direct)", "query": url, "opts": {}},
        {"name": "YouTube Music", "query": f"ytsearch1:{url}", "opts": {"default_search": "ytsearch"}},
        {"name": "YouTube", "query": f"ytsearch1:{url}", "opts": {}},
        {"name": "SoundCloud", "query": f"scsearch1:{url}", "opts": {}}
    ]

    success = False
    for step in priorities:
        try:
            await status_msg.edit_text(f'⏳ در حال تلاش از منبع: {step["name"]}...')
            
            current_opts = ydl_opts_base.copy()
            current_opts.update(step["opts"])

            with yt_dlp.YoutubeDL(current_opts) as ydl:
                info_dict = ydl.extract_info(step["query"], download=True)
                
                # مدیریت تفاوت فرمت خروجی جستجو و لینک مستقیم
                if 'entries' in info_dict:
                    if len(info_dict['entries']) > 0:
                        info = info_dict['entries'][0]
                    else: continue
                else:
                    info = info_dict
                
                filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
                
                if os.path.exists(filename):
                    await update.message.reply_audio(
                        audio=open(filename, 'rb'), 
                        caption=f"✅ دانلود موفق از: {step['name']}"
                    )
                    os.remove(filename)
                    success = True
                    break
        except Exception as e:
            print(f"Failed at {step['name']}: {e}")
            continue

    if success:
        await status_msg.delete()
    else:
        await status_msg.edit_text("❌ متأسفانه آهنگ در هیچ‌کدام از منابع (اسپاتیفای، یوتیوب، ساوندکلود) یافت نشد یا قفل امنیتی داشت.")

if __name__ == '__main__':
    if not TOKEN:
        print("❌ BOT_TOKEN یافت نشد!")
    else:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        print("🚀 ربات با سیستم اولویت‌بندی هوشمند فعال شد...")
        app.run_polling(drop_pending_updates=True)
