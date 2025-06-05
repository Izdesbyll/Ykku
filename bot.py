import os
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from telegram.ext import Application
from utils import gradual_translate_epub

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

user_targets = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me an EPUB file and tell me which language you'd like to learn (e.g. /setlang en)")

async def setlang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /setlang en (or es, fr, etc.)")
        return
    user_targets[update.effective_user.id] = context.args[0]
    await update.message.reply_text(f"Target language set to: {context.args[0]}")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target_lang = user_targets.get(user_id)
    if not target_lang:
        await update.message.reply_text("Please set a target language first using /setlang")
        return

    file = update.message.document or update.message.effective_attachment
    if not file.file_name.endswith(".epub"):
        await update.message.reply_text("Please upload an EPUB file.")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, file.file_name)
        output_path = os.path.join(tmpdir, "translated.epub")
        await file.get_file().download_to_drive(input_path)

        await update.message.reply_text("Translating book, please wait...")

        try:
            gradual_translate_epub(input_path, output_path, target_lang)
            await update.message.reply_document(document=open(output_path, "rb"), filename="translated.epub")
        except Exception as e:
            await update.message.reply_text(f"Translation failed: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setlang", setlang))
    app.add_handler(MessageHandler(filters.Document.MimeType.EPUB, handle_file))
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
