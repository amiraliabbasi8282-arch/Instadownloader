import os
import re
import shutil
import yt_dlp
import instaloader
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv('BOT_TOKEN')

# تنظیمات اینستاگرام
L = instaloader.Instaloader()
L.save_metadata = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'سلام! من ربات دانلودر همه‌کاره هستم. 🤖\n\n'
        'کافیه لینک یکی از سرویس‌های زیر رو بفرستی:\n'
        '🔹 اینستاگرام (Post, Reels)\n'
        '🔹 تیک‌تاک (TikTok)\n'
        '🔹 اسپاتیفای (Spotify Track)\n'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    status_msg = await update.message.reply_text('⏳ در حال پردازش لینک و آماده‌سازی برای دانلود...')

    # --- بخش اینستاگرام ---
    if "instagram.com" in url:
        try:
            match = re.search(r"/(?:p|reels|reel|tv)/([A-Za-z0-9_-]+)", url)
            if not match:
                await status_msg.edit_text("❌ کد پست اینستاگرام یافت نشد.")
                return
            
            shortcode = match.group(1)
            download_path = f"insta_{shortcode}"
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            L.download_post(post, target=download_path)

            for file in os.listdir(download_path):
                file_full = os.path.join(download_path, file)
                if file.endswith('.mp4'):
                    await update.message.reply_video(video=open(file_full, 'rb'), caption="خدمت شما! ✅")
                elif file.endswith('.jpg') and not any(f.endswith('.mp4') for f in os.listdir(download_path)):
                    await update.message.reply_photo(photo=open(file_full, 'rb'))
            
            shutil.rmtree(download_path)
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ خطای اینستاگرام: {str(e)}")

    # --- بخش تیک‌تاک و اسپاتیفای ---
    elif "tiktok.com" in url or "spotify.com" in url:
        is_spotify = "spotify.com" in url
        output_filename = 'music.mp3' if is_spotify else 'video.mp4'
        
        # تنظیمات yt-dlp برای دانلود هوشمند
        ydl_opts = {
            'outtmpl': output_filename,
            'quiet': True,
            'no_warnings': True,
        }
        
        # اگر اسپاتیفای بود، فقط صدا را استخراج کن
        if is_spotify:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if is_spotify:
                # ارسال فایل صوتی (اسپاتیفای)
                # نکته: نام فایل خروجی yt-dlp برای موزیک معمولاً .mp3 می‌شود
                final_file = 'music.mp3' 
                await update.message.reply_audio(audio=open(final_file, 'rb'), caption="آهنگ درخواستی شما از اسپاتیفای 🎵")
            else:
                # ارسال ویدیو (تیک‌تاک)
                final_file = 'video.mp4'
                await update.message.reply_video(video=open(final_file, 'rb'), caption="ویدیو تیک‌تاک شما ✅")
            
            if os.path.exists(final_file): os.remove(final_file)
            await status_msg.delete()

        except Exception as e:
            await status_msg.edit_text(f"❌ خطا در دانلود: ممکنه لینک اشتباه باشه یا سرور مسدود شده باشه.")
            print(f"Error: {e}")

    else:
        await status_msg.edit_text("❌ متأسفانه این لینک رو نمی‌شناسم. فعلاً فقط اینستا، تیک‌تاک و اسپاتیفای پشتیبانی می‌شه.")

if __name__ == '__main__':
    if not TOKEN:
        print("Error: BOT_TOKEN not found!")
    else:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        print("Bot is running with Spotify, TikTok and Instagram support...")
        app.run_polling(drop_pending_updates=True)
