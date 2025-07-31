import os
import random
import subprocess
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

LOGO_FOLDER = "logos"
FILTERS = [
    "filters/cinematic.lut",
    "filters/retro.lut",
    "filters/vivid.lut",
    "filters/boost.lut",
    "filters/light.lut",
]

if not os.path.exists(LOGO_FOLDER):
    os.makedirs(LOGO_FOLDER)

ASK_LOGO = range(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a public Facebook video link and I’ll add your logo with a professional filter!"
    )

async def handle_video_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    context.user_data["video_link"] = link
    await update.message.reply_text("Now send me the logo you want to add to this video (PNG/JPG).")
    return ASK_LOGO

async def handle_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # লোগো সেভ করা
    logo_path = f"{LOGO_FOLDER}/{update.message.from_user.id}.png"
    photo_file = await update.message.photo[-1].get_file()
    await photo_file.download_to_drive(logo_path)

    await update.message.reply_text("Processing your video with logo and filters... Please wait!")

    # ফেসবুক ভিডিও ডাউনলোড
    video_url = context.user_data["video_link"]
    video_file = "video.mp4"
    download_facebook_video(video_url, video_file)

    # ফিল্টার এবং লোগো প্রয়োগ
    filtered_video = "output.mp4"
    apply_filter_and_logo(video_file, logo_path, filtered_video)

    # ভিডিও সেন্ড করা
    with open(filtered_video, "rb") as f:
        await update.message.reply_video(video=f)

    # ক্লিনআপ
    os.remove(video_file)
    os.remove(filtered_video)
    os.remove(logo_path)
    return ConversationHandler.END

def download_facebook_video(url, filename):
    r = requests.get(url, stream=True)
    with open(filename, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            f.write(chunk)

def apply_filter_and_logo(video_path, logo_path, output_path):
    chosen_filter = random.choice(FILTERS)
    command = [
        "ffmpeg",  # Render এ ffmpeg system-wide ইনস্টল থাকে, তাই সরাসরি "ffmpeg"
        "-i", video_path,
        "-i", logo_path,
        "-filter_complex", f"[0:v]lut3d=file={chosen_filter}[v];[v][1:v]overlay=W-w-10:H-h-10",
        "-c:a", "copy",
        output_path
    ]
    subprocess.run(command, check=True)

conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_link)],
    states={
        ASK_LOGO: [MessageHandler(filters.PHOTO, handle_logo)]
    },
    fallbacks=[]
)

def main():
    token = os.getenv("BOT_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
