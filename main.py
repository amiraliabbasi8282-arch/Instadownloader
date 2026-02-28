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
    await update.message.reply_text('🚀 ربات همه‌کاره دانلودر آماده است!\n\n🔹 لینک (یوتیوب، اینستا، اسپاتیفای و...)\n🔹 یا اسم آهنگ (مثلاً: ابی پوست شیر)\nرو بفرست برات دانلود کنم.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    ffmpeg_path = get_ffmpeg_path()
    
    # تشخیص یوتیوب
    if "youtube.com" in text or "youtu.be" in text:
        keyboard = [[InlineKeyboardButton("🎬 ویدیو", callback_data=f"yt_list|{text}"),
                     InlineKeyboardButton("🎵 آهنگ", callback_data=f"yt_audio|{text}")]]
        await update.message.reply_text("چه فرمتی مد نظرت هست؟", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    status_msg = await update.message.reply_text('⏳ در حال جستجو و پردازش...')

    # تشخیص اینستاگرام
    if "instagram.com" in text:
        try:
            match = re.search(r"/(?:p|reels|reel|tv)/([A-Za-z0-9_-]+)", text)
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
            return
        except: return await status_msg.edit_text("❌ خطا در اینستاگرام")

    # بخش موزیک (لینک اسپاتیفای/ساوندکلود یا جستجوی نام آهنگ)
    is_link = text.startswith("http")
    query = f"ytsearch1:{text}" if not is_link or "spotify" in text else text
    
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
            if 'entries' in info:
                if not info['entries']:
                    return await status_msg.edit_text("❌ متاسفانه آهنگی پیدا نشد.")
                info = info['entries'][0]

            fname = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
            
            # پیدا کردن تصویر کاور
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
            else:
                await status_msg.edit_text("❌ خطا در دریافت فایل صوتی.")
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا: {str(e)[:50]}")

# --- بخش Callback برای یوتیوب ---
async def yt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    action, url = data[0], data[1]
    ffmpeg_path = get_ffmpeg_path()

    if action == "yt_audio":
        await query.edit_message_text("⏳ در حال دانلود آهنگ یوتیوب...")
        opts = {
            'format': 'bestaudio/best', 'outtmpl': 'yt_a.%(ext)s', 'writethumbnail': True, 'ffmpeg_location': ffmpeg_path,
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}, {'key': 'FFmpegMetadata'}, {'key': 'EmbedThumbnail'}]
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title, artist = info.get('title', 'Unknown'), info.get('uploader', 'Unknown')
                thumb = next((f for f in os.listdir('.') if f.endswith(('.jpg', '.webp')) and f.startswith('yt_a')), None)
                if thumb: await query.message.reply_photo(photo=open(thumb, 'rb'), caption=f"🎵 **{title}**\n👤 {artist}", parse_mode='Markdown')
                await query.message.reply_audio(audio=open('yt_a.mp3', 'rb'), title=title, performer=artist)
                for f in ['yt_a.mp3', thumb]: 
                    if f and os.path.exists(f): os.remove(f)
                await query.message.delete()
        except: await query.edit_message_text("❌ خطا در دانلود صوت یوتیوب.")

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
                if os.path.exists('v.mp4'): os.remove('v.mp4')
                await query.message.delete()
        except: await query.edit_message_text("❌ خطا در دانلود ویدیو.")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(yt_callback, pattern="^yt_"))
    app.run_polling()
