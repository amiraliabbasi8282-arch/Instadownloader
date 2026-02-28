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
INSTA_USER = os.getenv('INSTA_USER')
INSTA_PASS = os.getenv('INSTA_PASS')

def get_ffmpeg_path():
    for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/nix/var/nix/profiles/default/bin/ffmpeg']:
        if os.path.exists(path): return path
    try:
        return subprocess.check_output(['which', 'ffmpeg']).decode('utf-8').strip()
    except: return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🚀 ربات پیشرفته دانلودر آماده است!\n\nلینک موزیک یا ویدیو بفرست تا فایل + کاور (همراه با مشخصات) رو برات بفرستم.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): return

    # مدیریت یوتیوب
    if "youtube.com" in url or "youtu.be" in url:
        keyboard = [[InlineKeyboardButton("🎬 ویدیو", callback_data=f"yt_list|{url}"),
                     InlineKeyboardButton("🎵 آهنگ", callback_data=f"yt_audio|{url}")]]
        await update.message.reply_text("فرمت را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    status_msg = await update.message.reply_text('⏳ در حال پردازش...')
    ffmpeg_path = get_ffmpeg_path()

    # مدیریت اسپاتیفای و ساوندکلود و پینترست/تیک‌تاک
    is_music = any(x in url for x in ["spotify", "soundcloud"])
    
    ydl_opts = {
        'outtmpl': 'file_%(title)s.%(ext)s',
        'quiet': True,
        'writethumbnail': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }
    if ffmpeg_path: ydl_opts['ffmpeg_location'] = ffmpeg_path

    if is_music:
        query = f"ytsearch1:{url}" if "spotify" in url else url
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'},
                {'key': 'FFmpegMetadata'},
                {'key': 'EmbedThumbnail'}
            ]
        })
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                if 'entries' in info: info = info['entries'][0]
                fname = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
                
                # پیدا کردن کاور
                thumbnail = None
                for f in os.listdir('.'):
                    if f.endswith(('.jpg', '.webp', '.png')) and not f.startswith('file_'):
                        thumbnail = f; break

                if os.path.exists(fname):
                    title = info.get('title', 'نامشخص')
                    artist = info.get('uploader', 'نامشخص')
                    caption_text = f"🎵 **Song:** {title}\n👤 **Artist:** {artist}"

                    if thumbnail:
                        await update.message.reply_photo(photo=open(thumbnail, 'rb'), caption=caption_text, parse_mode='Markdown')
                    
                    await update.message.reply_audio(audio=open(fname, 'rb'), title=title, performer=artist)
                    
                    if os.path.exists(fname): os.remove(fname)
                    if thumbnail and os.path.exists(thumbnail): os.remove(thumbnail)
                    await status_msg.delete()
                    return
        except Exception as e:
            await status_msg.edit_text(f"❌ خطا: {str(e)[:50]}")
            return

    # بخش اینستاگرام (به اختصار)
    if "instagram.com" in url:
        # کد اینستاگرام طبق روال قبل...
        pass

async def yt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    action, url = data[0], data[1]
    ffmpeg_path = get_ffmpeg_path()

    if action == "yt_audio":
        await query.edit_message_text("⏳ در حال آماده‌سازی آهنگ و کاور...")
        opts = {
            'format': 'bestaudio/best', 'outtmpl': 'a.%(ext)s', 'writethumbnail': True, 'ffmpeg_location': ffmpeg_path,
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}, {'key': 'FFmpegMetadata'}, {'key': 'EmbedThumbnail'}]
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'نامشخص')
                artist = info.get('uploader', 'نامشخص')
                
                thumb = None
                for f in os.listdir('.'):
                    if f.endswith(('.jpg', '.webp')) and f.startswith('a'): thumb = f; break
                
                caption_text = f"🎵 **Song:** {title}\n👤 **Artist:** {artist}"
                
                if thumb:
                    await query.message.reply_photo(photo=open(thumb, 'rb'), caption=caption_text, parse_mode='Markdown')
                
                await query.message.reply_audio(audio=open('a.mp3', 'rb'), title=title, performer=artist)
                
                if os.path.exists('a.mp3'): os.remove('a.mp3')
                if thumb and os.path.exists(thumb): os.remove(thumb)
                await query.message.delete()
        except:
            await query.edit_message_text("❌ خطا در پردازش آهنگ یوتیوب")

    elif action == "yt_list":
        # کد نمایش کیفیت‌ها طبق روال قبل...
        pass

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(yt_callback, pattern="^yt_"))
    app.run_polling()
