import os
import re
import shutil
import yt_dlp
import instaloader
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv('BOT_TOKEN')
INSTA_USER = os.getenv('INSTA_USER')
INSTA_PASS = os.getenv('INSTA_PASS')

L = instaloader.Instaloader()
if INSTA_USER and INSTA_PASS:
    try:
        L.login(INSTA_USER, INSTA_PASS)
        print("✅ Instagram Login OK")
    except:
        print("❌ Instagram Login Failed")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('سلام! لینک اینستا، تیک‌تاک یا اسپاتیفای بفرست 📥')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    status = await update.message.reply_text('⏳ در حال دانلود...')

    if "instagram.com" in url:
        try:
            shortcode = re.search(r"/(?:p|reels|reel|tv)/([A-Za-z0-9_-]+)", url).group(1)
            path = f"insta_{shortcode}"
            L.download_post(instaloader.Post.from_shortcode(L.context, shortcode), target=path)
            for f in os.listdir(path):
                if f.endswith('.mp4'): await update.message.reply_video(video=open(f"{path}/{f}", 'rb'))
            shutil.rmtree(path)
            await status.delete()
        except Exception as e:
            await status.edit_text(f"❌ خطای اینستا: {str(e)[:50]}")

    elif "tiktok.com" in url or "spotify" in url:
        is_spotify = "spotify" in url
        ydl_opts = {
            'outtmpl': 'dl_file.%(ext)s',
            'quiet': True,
            'ffmpeg_location': '/usr/bin/ffmpeg' # آدرس استاندارد در لینوکس
        }
        if is_spotify:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            ext = 'mp3' if is_spotify else 'mp4'
            f_name = f'dl_file.{ext}'
            
            if os.path.exists(f_name):
                if is_spotify: await update.message.reply_audio(audio=open(f_name, 'rb'))
                else: await update.message.reply_video(video=open(f_name, 'rb'))
                os.remove(f_name)
                await status.delete()
            else:
                await status.edit_text("❌ FFmpeg پیدا نشد. متغیر NIXPACKS_PKGS را در Railway اضافه کنید.")
        except Exception as e:
            await status.edit_text(f"❌ خطا: {str(e)[:50]}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
