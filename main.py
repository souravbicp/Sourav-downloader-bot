import os
import random
import subprocess
import requests
from flask import Flask, request
from telegram import Update, Bot, InputFile
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, ConversationHandler

# Environment variables
TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# Flask app
app = Flask(__name__)
bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

# Logo folder
LOGO_FOLDER = "logos"
FILTERS = [
    "cinematic.lut",
    "retro.lut",
    "vivid.lut",
    "boost.lut",
    "light.lut"
]

if not os.path.exists(LOGO_FOLDER):
    os.makedirs(LOGO_FOLDER)

ASK_LOGO = 1

# Start command
def start(update, context):
    update.message.reply_text("Send me a Facebook video link, then send your logo image (PNG/JPG).")

# Step 1: Get video link
def receive_video_link(update, context):
    context.user_data["video_link"] = update.message.text
    update.message.reply_text("Got the video link! Now send your logo image.")
    return ASK_LOGO

# Step 2: Get logo and process
def receive_logo(update, context):
    user_id = update.message.from_user.id
    logo_path = os.path.join(LOGO_FOLDER, f"{user_id}.png")

    # Download logo
    photo_file = update.message.photo[-1].get_file()
    photo_file.download(logo_path)

    update.message.reply_text("Processing your video, please wait...")

    video_url = context.user_data.get("video_link")
    if not video_url:
        update.message.reply_text("No video link found. Please send the video link first.")
        return ConversationHandler.END

    video_file = f"{user_id}_video.mp4"
    output_file = f"{user_id}_output.mp4"

    # Download Facebook video
    def download_facebook_video(url, filename):
        r = requests.get(url, stream=True)
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)

    # Apply filter and logo
    def apply_filter_and_logo(video_path, logo_path, output_path):
        chosen_filter = random.choice(FILTERS)
        command = [
            "ffmpeg",
            "-i", video_path,
            "-i", logo_path,
            "-filter_complex", f"[0:v]lut3d=file={chosen_filter}[v];[v][1:v]overlay=W-w-10:H-h-10",
            "-c:a", "copy",
            output_path
        ]
        subprocess.run(command, check=True)

    try:
        download_facebook_video(video_url, video_file)
        apply_filter_and_logo(video_file, logo_path, output_file)
    except Exception as e:
        update.message.reply_text(f"Error processing video: {e}")
        return ConversationHandler.END

    # Send processed video
    with open(output_file, "rb") as f:
        update.message.reply_video(video=InputFile(f))

    # Cleanup
    for fpath in [video_file, output_file, logo_path]:
        if os.path.exists(fpath):
            os.remove(fpath)

    return ConversationHandler.END

conv_handler = ConversationHandler(
    entry_points=[MessageHandler(Filters.text & ~Filters.command, receive_video_link)],
    states={ASK_LOGO: [MessageHandler(Filters.photo, receive_logo)]},
    fallbacks=[]
)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(conv_handler)

# Webhook routes
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

@app.route("/")
def index():
    return "Telegram bot is running!"

if __name__ == "__main__":
    bot.set_webhook(WEBHOOK_URL + TOKEN)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
