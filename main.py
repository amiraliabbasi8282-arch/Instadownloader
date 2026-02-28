import os
import re
import shutil
import yt_dlp
import instaloader
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# --- تنظیمات متغیرها ---
TOKEN = os.getenv('BOT_TOKEN')
INSTA_USER = os.getenv('INSTA_USER')
INSTA_PASS = os.getenv('INSTA_PASS')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🚀 ربات دانلودر حرفه‌ای آماده است!\n\n🔹 لینک (یوتیوب، اسپاتیفای و...)\n🔹 یا اسم آهنگ (مثلاً: ابی مداد رنگی)\nرو بفرست تا با تگ اختصاصی برات بفرستم.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text: return

    # یوتیوب
    if "youtube.com" in text or "youtu.be" in text:
        keyboard = [[InlineKeyboardButton("🎬 ویدیو", callback_data=f"yt_list|{text}"),
                     InlineKeyboardButton("🎵 آهنگ", callback_data=f"yt_audio|{text}")]]
        await update.message.reply_text("فرمت مورد نظر:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    status_msg = await update.message.reply_text('⏳ در حال جستجو و پردازش...')

    # بخش موزیک (اسپاتیفای، ساوندکلود و جستجوی نام)
    is_link = text.startswith("http")
    query = f"ytsearch1:{text}" if not is_link or "spotify" in text else text
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'music_%(title)s.%(ext)s',
        'writethumbnail': True,
        'quiet': True,
        'prefer_ffmpeg': True,
        'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'},
            {'key': 'EmbedThumbnail'}
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            if 'entries' in info: info = info['entries'][0]

            fname = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
            
            # پیدا کردن تصویر کاور
            thumbnail = None
            for f in os.listdir('.'):
                if f.endswith(('.jpg', '.webp', '.png')) and not f.startswith('music_'):
                    thumbnail = f; break

            if os.path.exists(fname):
                # --- تفکیک هوشمند تگ‌ها ---
                raw_title = info.get('title', 'Unknown')
                artist = info.get('artist') or info.get('uploader') or "Unknown Artist"
                song = info.get('track') or raw_title
                
                # اگر در عنوان خط تیره بود، جدا کن
                if " - " in raw_title and not info.get('track'):
                    parts = raw_title.split(" - ", 1)
                    artist, song = parts[0], parts[1]

                # حذف کلمات اضافی یوتیوب
                song = re.sub(r'[\(\[].*?[\)\]]', '', song).strip()

                # ۱. ارسال کاور با کپشن
                if thumbnail:
                    await update.message.reply_photo(
                        photo=open(thumbnail, 'rb'), 
                        caption=f"🎵 **Song:** {song}\n👤 **Artist:** {artist}", 
                        parse_mode='Markdown'
                    )
                
                # ۲. ارسال آهنگ با تگ‌های مجزا
                await update.message.reply_audio(
                    audio=open(fname, 'rb'),
                    title=song,        # قرارگیری در بخش Song Name
                    performer=artist,   # قرارگیری در بخش Artist
                    thumbnail=open(thumbnail, 'rb') if thumbnail else None
                )
                
                # پاکسازی فایل‌ها
                if os.path.exists(fname): os.remove(fname)
                if thumbnail: os.remove(thumbnail)
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ خطا در دانلود فایل.")
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا: {str(e)[:100]}")

# --- بخش یوتیوب ---
async def yt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    action, url = data[0], data[1]

    if action == "yt_audio":
        await query.edit_message_text("⏳ در حال تبدیل به آهنگ...")
        opts = {
            'format': 'bestaudio/best', 'outtmpl': 'yt_a.%(ext)s', 'writethumbnail': True,
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}, {'key': 'EmbedThumbnail'}]
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                raw_title = info.get('title', 'Unknown')
                artist = info.get('uploader', 'Unknown Artist')
                song = raw_title
                
                if " - " in raw_title:
                    parts = raw_title.split(" - ", 1)
                    artist, song = parts[0], parts[1]
                
                song = re.sub(r'[\(\[].*?[\)\]]', '', song).strip()
                thumb = next((f for f in os.listdir('.') if f.endswith(('.jpg', '.webp')) and f.startswith('yt_a')), None)
                
                if thumb: await query.message.reply_photo(photo=open(thumb, 'rb'), caption=f"🎵 **{song}**\n👤 {artist}", parse_mode='Markdown')
                await query.message.reply_audio(audio=open('yt_a.mp3', 'rb'), title=song, performer=artist)
                
                for f in ['yt_a.mp3', thumb]:
                    if f and os.path.exists(f): os.remove(f)
                await query.message.delete()
        except Exception as e:
            await query.edit_message_text(f"❌ خطا: {str(e)[:50]}")

    elif action == "yt_list":
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            heights = sorted(list(set(f.get('height') for f in info['formats'] if f.get('height') and f.get('height') <= 1080)), reverse=True)
            btns = [[InlineKeyboardButton(f"🎬 {h}p", callback_data=f"yt_dl|{url}|{h}")] for h in heights[:5]]
            await query.edit_message_text("کیفیت ویدیو:", reply_markup=InlineKeyboardMarkup(btns))

    elif action == "yt_dl":
        res = data[2]
        await query.edit_message_text(f"⏳ دانلود ویدیو با کیفیت {res}p...")
        opts = {'format': f'bestvideo[height<={res}][ext=mp4]+bestaudio/best', 'outtmpl': 'v.mp4'}
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
