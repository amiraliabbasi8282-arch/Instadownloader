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
    await update.message.reply_text('🚀 ربات همه‌کاره آماده است!\nلینک یوتیوب، اسپاتیفای، اینستاگرام یا ساوندکلود بفرست.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): return

    if "youtube.com" in url or "youtu.be" in url:
        keyboard = [[InlineKeyboardButton("🎬 ویدیو", callback_data=f"yt_list|{url}"),
                     InlineKeyboardButton("🎵 آهنگ", callback_data=f"yt_audio|{url}")]]
        await update.message.reply_text("چه فرمتی مد نظرت هست؟", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    status_msg = await update.message.reply_text('⏳ در حال پردازش...')
    ffmpeg_path = get_ffmpeg_path()

    # مدیریت اسپاتیفای و ساوندکلود
    is_music = any(x in url for x in ["spotify", "soundcloud"])
    
    if is_music:
        query = f"ytsearch1:{url}" if "spotify" in url else url
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'music_%(title)s.%(ext)s',
            'writethumbnail': True,
            'quiet': True,
            'ffmpeg_location': ffmpeg_path,
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'},
                {'key': 'FFmpegMetadata'},
                {'key': 'EmbedThumbnail'}
            ],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                
                # رفع ارور list index out of range
                if 'entries' in info:
                    if not info['entries']:
                        return await status_msg.edit_text("❌ متاسفانه این آهنگ پیدا نشد.")
                    info = info['entries'][0]

                fname = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
                
                # پیدا کردن کاور دانلود شده
                thumbnail = None
                for f in os.listdir('.'):
                    if f.endswith(('.jpg', '.webp', '.png')) and not f.startswith('music_'):
                        thumbnail = f; break

                if os.path.exists(fname):
                    title = info.get('title', 'Unknown')
                    artist = info.get('uploader', 'Unknown')
                    caption = f"🎵 **Song:** {title}\n👤 **Artist:** {artist}"
                    
                    if thumbnail:
                        await update.message.reply_photo(photo=open(thumbnail, 'rb'), caption=caption, parse_mode='Markdown')
                    
                    await update.message.reply_audio(audio=open(fname, 'rb'), title=title, performer=artist)
                    
                    if os.path.exists(fname): os.remove(fname)
                    if thumbnail: os.remove(thumbnail)
                    await status_msg.delete()
                    return
        except Exception as e:
            return await status_msg.edit_text(f"❌ خطا در موزیک: {str(e)[:50]}")

    # سایر منابع (اینستاگرام، تیک‌تاک، پینترست)
    # ... (کدهای اینستاگرام و پینترست در اینجا قرار می‌گیرند)
    await status_msg.edit_text("❌ لینک شناسایی نشد یا منبع معتبر نیست.")

async def yt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    action, url = data[0], data[1]
    ffmpeg_path = get_ffmpeg_path()

    if action == "yt_audio":
        await query.edit_message_text("⏳ در حال استخراج آهنگ و کاور...")
        opts = {
            'format': 'bestaudio/best', 'outtmpl': 'yt_a.%(ext)s', 'writethumbnail': True, 'ffmpeg_location': ffmpeg_path,
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}, {'key': 'FFmpegMetadata'}, {'key': 'EmbedThumbnail'}]
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title, artist = info.get('title', 'Unknown'), info.get('uploader', 'Unknown')
                
                thumb = None
                for f in os.listdir('.'):
                    if f.endswith(('.jpg', '.webp')) and f.startswith('yt_a'): thumb = f; break
                
                caption = f"🎵 **Song:** {title}\n👤 **Artist:** {artist}"
                if thumb: await query.message.reply_photo(photo=open(thumb, 'rb'), caption=caption, parse_mode='Markdown')
                await query.message.reply_audio(audio=open('yt_a.mp3', 'rb'), title=title, performer=artist)
                
                if os.path.exists('yt_a.mp3'): os.remove('yt_a.mp3')
                if thumb: os.remove(thumb)
                await query.message.delete()
        except: await query.edit_message_text("❌ خطا در استخراج صوت.")

    elif action == "yt_list":
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            heights = sorted(list(set(f.get('height') for f in info['formats'] if f.get('height') and f.get('height') <= 1080)), reverse=True)
            btns = [[InlineKeyboardButton(f"🎬 {h}p", callback_data=f"yt_dl|{url}|{h}")] for h in heights[:5]]
            await query.edit_message_text("کیفیت ویدیو را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(btns))

    elif action == "yt_dl":
        res = data[2]
        await query.edit_message_text(f"⏳ دانلود ویدیو {res}p...")
        opts = {'format': f'bestvideo[height<={res}][ext=mp4]+bestaudio/best', 'outtmpl': 'v.mp4', 'ffmpeg_location': ffmpeg_path}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
                await query.message.reply_video(video=open('v.mp4', 'rb'))
                os.remove('v.mp4')
                await query.message.delete()
        except: await query.edit_message_text("❌ خطا در دانلود ویدیو.")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(yt_callback, pattern="^yt_"))
    app.run_polling()
