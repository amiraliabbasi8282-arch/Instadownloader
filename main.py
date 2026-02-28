import os
import re
import yt_dlp
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.getenv('BOT_TOKEN')

def get_ffmpeg_path():
    for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/nix/var/nix/profiles/default/bin/ffmpeg']:
        if os.path.exists(path): return path
    try:
        return subprocess.check_output(['which', 'ffmpeg']).decode('utf-8').strip()
    except: return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('📥 لینک یوتیوب را بفرست تا با کیفیت دلخواه برات دانلود کنم!')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): return

    if "youtube.com" in url or "youtu.be" in url:
        keyboard = [
            [
                InlineKeyboardButton("🎬 انتخاب کیفیت ویدیو", callback_data=f"yt_list|{url}"),
                InlineKeyboardButton("🎵 آهنگ (MP3)", callback_data=f"yt_audio|{url}"),
            ]
        ]
        await update.message.reply_text("چه قالبی مد نظرت هست؟", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("|")
    action = data[0] # yt_list, yt_format, yt_audio
    url = data[1]
    
    ffmpeg_path = get_ffmpeg_path()

    # مرحله ۱: نمایش لیست کیفیت‌ها
    if action == "yt_list":
        await query.edit_message_text("🔍 در حال استخراج کیفیت‌های موجود...")
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = info.get('formats', [])
                
                # فیلتر کردن کیفیت‌های رایج (فقط MP4 و دارای رزولوشن)
                available_resolutions = []
                seen_heights = set()
                
                for f in formats:
                    height = f.get('height')
                    if height and height not in seen_heights and f.get('vcodec') != 'none':
                        # محدودیت برای تلگرام (معمولاً زیر 720p برای حجم مناسب)
                        if height <= 1080: 
                            seen_heights.add(height)
                            available_resolutions.append(height)
                
                available_resolutions.sort(reverse=True)
                keyboard = []
                for res in available_resolutions:
                    keyboard.append([InlineKeyboardButton(f"🎬 {res}p", callback_data=f"yt_format|{url}|{res}")])
                
                await query.edit_message_text(f"کیفیت مورد نظر برای «{info.get('title')[:30]}...» را انتخاب کنید:", 
                                              reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در استخراج: {str(e)[:50]}")

    # مرحله ۲: دانلود کیفیت انتخاب شده
    elif action == "yt_format":
        res = data[2]
        status_msg = await query.edit_message_text(text=f"⏳ در حال دانلود با کیفیت {res}p...")
        
        ydl_opts = {
            'format': f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res}]',
            'outtmpl': '%(title)s_%(height)p.%(ext)s',
            'quiet': True,
        }
        if ffmpeg_path: ydl_opts['ffmpeg_location'] = ffmpeg_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                if os.path.exists(filename):
                    await query.message.reply_video(video=open(filename, 'rb'), caption=f"✅ کیفیت: {res}p")
                    os.remove(filename)
                    await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ خطا در دانلود: {str(e)[:50]}")

    # مرحله ۳: دانلود صوتی (با کاور و تگ - طبق کد قبلی)
    elif action == "yt_audio":
        status_msg = await query.edit_message_text(text="⏳ در حال تبدیل به MP3 با کاور...")
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
            'writethumbnail': True,
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                {'key': 'FFmpegMetadata'},
                {'key': 'EmbedThumbnail'},
            ],
        }
        if ffmpeg_path: ydl_opts['ffmpeg_location'] = ffmpeg_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
                if os.path.exists(filename):
                    await query.message.reply_audio(audio=open(filename, 'rb'), title=info.get('title'), performer=info.get('uploader'))
                    os.remove(filename)
                    await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ خطا: {str(e)[:50]}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^yt_"))
    print("🚀 ربات پیشرفته یوتیوب روشن شد...")
    app.run_polling(drop_pending_updates=True)
