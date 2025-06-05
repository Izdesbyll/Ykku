from ebooklib import epub
from ebooklib import ITEM_DOCUMENT
from bs4 import BeautifulSoup
from collections import Counter
import re
from googletrans import Translator

def extract_text_from_epub(epub_path):
    book = epub.read_epub(epub_path)
    text_by_page = []
    for item in book.items:
        if item.get_type() == ITEM_DOCUMENT:
            soup = BeautifulSoup(item.content, 'html.parser')
            text = soup.get_text()
            text_by_page.append(text)
    return text_by_page

def clean_and_tokenize(text):
    return re.findall(r'\b\w+\b', text.lower())

def replace_words(text, replacements):
    def replacer(match):
        word = match.group(0)
        return replacements.get(word.lower(), word)

    if not replacements:
        return text

    pattern = r'\b(' + '|'.join(re.escape(word) for word in replacements) + r')\b'
    return re.sub(pattern, replacer, text, flags=re.IGNORECASE)

def detect_source_language(text):
    translator = Translator()
    detection = translator.detect(text)
    return detection.lang

def convert_text_to_epub(text_paragraphs, output_path, title="Gradual Translation", author="Booklingual Bot"):
    book = epub.EpubBook()
    book.set_title(title)
    book.set_language('en')
    book.add_author(author)

    chapters = []
    chapter = epub.EpubHtml(title='Translated Book', file_name='translated.xhtml', lang='en')
    body = ""
    for para in text_paragraphs:
        safe_para = para.replace("\n", "<br/>")
        body += f"<p>{safe_para}</p>\n"

    chapter.content = f"<html><body>{body}</body></html>"
    book.add_item(chapter)
    chapters.append(chapter)

    book.toc = chapters
    book.spine = ['nav'] + chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(output_path, book)

def gradual_translate_epub(epub_input_path, epub_output_path, target_lang, max_words=200):
    pages = extract_text_from_epub(epub_input_path)
    paragraphs = []
    for page in pages:
        split_paragraphs = [p.strip() for p in page.split('\n') if p.strip()]
        paragraphs.extend(split_paragraphs)

    translator = Translator()
    translated_words = {}
    seen_words = set()

    sample_text = " ".join(paragraphs[:5])
    source_lang = detect_source_language(sample_text)
    print(f"Detected source language: {source_lang}")

    i = 0
    while i < len(paragraphs) and len(translated_words) < max_words:
        group = paragraphs[i:i+3]
        all_text = ' '.join(group)
        words = clean_and_tokenize(all_text)
        word_freq = Counter(words)

        for j in range(i, len(paragraphs)):
            paragraphs[j] = replace_words(paragraphs[j], translated_words)

        new_words = [
            w for w, _ in word_freq.most_common()
            if w not in seen_words and not (source_lang == 'en' and w.lower() == 'a')
        ]
        if new_words:
            word_to_translate = new_words[0]
            try:
                translated = translator.translate(word_to_translate, src=source_lang, dest=target_lang).text
                translated_words[word_to_translate] = translated
                seen_words.add(word_to_translate)
                for j in range(i, len(paragraphs)):
                    paragraphs[j] = replace_words(paragraphs[j], translated_words)
            except Exception as e:
                print(f"Translation failed for '{word_to_translate}': {e}")

        i += 3

    convert_text_to_epub(paragraphs, epub_output_path)
