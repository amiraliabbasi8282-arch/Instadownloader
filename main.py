import os
import re
import shutil
import yt_dlp
import instaloader
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- تنظیمات اولیه ---
TOKEN = os.getenv('BOT_TOKEN')
INSTA_USER = os.getenv('INSTA_USER')
INSTA_PASS = os.getenv('INSTA_PASS')

# تنظیمات اینستاگرام
L = instaloader.Instaloader()
L.save_metadata = False
if INSTA_USER and INSTA_PASS:
    try:
        L.login(INSTA_USER, INSTA_PASS)
        print("✅ Logged into Instagram!")
    except Exception as e:
        print(f"⚠️ Instagram Login Failed: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'سلام! من ربات دانلودر همه‌کاره هستم. 📥\n\n'
        'کافیه لینک پست یا ریلز اینستاگرام، تیک‌تاک یا آهنگ اسپاتیفای رو بفرستی تا برات دانلود کنم.'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    status_msg = await update.message.reply_text('⏳ در حال پردازش و دانلود (لطفاً صبور باشید)...')

    # --- تشخیص نوع لینک ---
    # ۱. اینستاگرام
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
                f_path = os.path.join(download_path, file)
                if file.endswith('.mp4'):
                    await update.message.reply_video(video=open(f_path, 'rb'), caption="بفرما! ✅")
                elif file.endswith('.jpg') and not any(f.endswith('.mp4') for f in os.listdir(download_path)):
                    await update.message.reply_photo(photo=open(f_path, 'rb'))
            
            shutil.rmtree(download_path)
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ خطای اینستاگرام: {str(e)[:50]}")

    # ۲. تیک‌تاک و اسپاتیفای (با استفاده از yt-dlp)
    elif "tiktok.com" in url or "spotify.com" in url:
        is_spotify = "spotify.com" in url
        output_template = 'downloaded_file.%(ext)s'
        
        ydl_opts = {
            'outtmpl': 'downloaded_file',
            'quiet': True,
            'no_warnings': True,
        }

        if is_spotify:
            # تنظیمات مخصوص تبدیل به MP3 برای اسپاتیفای
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            # تنظیمات ویدیو برای تیک‌تاک
            ydl_opts.update({'format': 'bestvideo+bestaudio/best'})

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if is_spotify:
                final_file = 'downloaded_file.mp3'
                await update.message.reply_audio(audio=open(final_file, 'rb'), caption="آهنگ اسپاتیفای شما 🎵")
            else:
                final_file = 'downloaded_file.mp4' # یا هر پسوند ویدیویی دیگر
                # پیدا کردن فایل ویدیو چون ممکنه پسوندش متفاوت باشه
                for f in os.listdir('.'):
                    if f.startswith('downloaded_file') and not f.endswith('.py'):
                        await update.message.reply_video(video=open(f, 'rb'), caption="ویدیو تیک‌تاک شما ✅")
                        os.remove(f)
                        break
            
            if os.path.exists('downloaded_file.mp3'): os.remove('downloaded_file.mp3')
            await status_msg.delete()

        except Exception as e:
            print(f"Download Error: {e}")
            await status_msg.edit_text("❌ خطا در دانلود. مطمئن شوید FFmpeg نصب است.")

    else:
        await status_msg.edit_text("❌ این لینک پشتیبانی نمی‌شود.")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is Running...")
    app.run_polling(drop_pending_updates=True)
