import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from deep_translator import GoogleTranslator
from ebooklib import epub
from bs4 import BeautifulSoup
import tempfile

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me an EPUB file to gradually translate it!")

def extract_text_and_translate(epub_path, target_lang):
    book = epub.read_epub(epub_path)
    translated_book = epub.EpubBook()
    translated_book.set_identifier("translated")
    translated_book.set_title("Translated Book")
    translated_book.set_language(target_lang)

    added_words = {}
    all_paragraphs = []
    new_items = []

    for item in book.items:
        if isinstance(item, epub.EpubHtml):
            soup = BeautifulSoup(item.get_body_content(), "html.parser")
            paragraphs = soup.find_all("p")
            translated_paragraphs = []

            for i, p in enumerate(paragraphs):
                text = p.get_text()
                words = text.split()
                if i % 3 == 0:
                    freqs = {}
                    for word in words:
                        lw = word.lower().strip(".,!?;:'\"“”")
                        if lw and lw not in added_words and lw != "a":
                            freqs[lw] = freqs.get(lw, 0) + 1
                    if freqs:
                        top_word = max(freqs, key=freqs.get)
                        translated = GoogleTranslator(source='auto', target=target_lang).translate(top_word)
                        added_words[top_word] = translated

                new_text = " ".join(added_words.get(w.lower().strip(".,!?;:'\"“”"), w) for w in words)
                p.string = new_text
                translated_paragraphs.append(p)

            item.set_content(str(soup).encode("utf-8"))
            new_items.append(item)
        else:
            new_items.append(item)

    for item in new_items:
        translated_book.add_item(item)

    for item in book.spine:
        if isinstance(item, tuple):
            translated_book.spine.append(item)
    translated_book.add_item(epub.EpubNcx())
    translated_book.add_item(epub.EpubNav())

    with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp:
        epub.write_epub(tmp.name, translated_book)
        return tmp.name

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if doc.mime_type != "application/epub+zip":
        await update.message.reply_text("Please send a valid EPUB file.")
        return

    user_data = context.user_data
    target_lang = user_data.get("target_lang", "en")

    file_path = await doc.get_file()
    file_name = os.path.join(tempfile.gettempdir(), doc.file_name)
    await file_path.download_to_drive(file_name)

    await update.message.reply_text("Translating your EPUB file. This may take a moment...")

    translated_path = extract_text_and_translate(file_name, target_lang)

    with open(translated_path, "rb") as f:
        await update.message.reply_document(f, filename="translated.epub")

    os.remove(file_name)
    os.remove(translated_path)

async def setlang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /setlang [target_language_code]")
        return
    context.user_data["target_lang"] = context.args[0]
    await update.message.reply_text(f"Target language set to: {context.args[0]}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setlang", setlang))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.run_polling()

if __name__ == "__main__":
    main()
