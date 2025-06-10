from ebooklib import epub, ITEM_DOCUMENT  # ✅ fix here
from bs4 import BeautifulSoup
from collections import Counter
import re
from googletrans import Translator
import string

SOURCE_LANG = 'en'  # your book's original language
TARGET_LANG = 'is'  # language you want to learn

def reverse_first_char_case(input_string):
    if not input_string:
        return input_string
    first_char = input_string[0]
    if first_char.isupper():
        reversed_char = first_char.lower()
    elif first_char.islower():
        reversed_char = first_char.upper()
    else:
        reversed_char = first_char
    return reversed_char + input_string[1:]

def extract_text_from_epub(epub_path):
    book = epub.read_epub(epub_path)
    text_by_page = []
    for item in book.items:
        if item.get_type() == ITEM_DOCUMENT:  # ✅ fix here
            soup = BeautifulSoup(item.content, 'html.parser')
            text = soup.get_text()
            text_by_page.append(text)
    return text_by_page


def clean_and_tokenize(text):
    return re.findall(r'\b\w+\b', text.lower())



def replace_words(text, replacements):
    def replacer(match):
        word = match.group(0)

        # Separate punctuation
        prefix = ''
        suffix = ''
        core = word

        while core and core[0] in string.punctuation:
            prefix += core[0]
            core = core[1:]
        while core and core[-1] in string.punctuation:
            suffix = core[-1] + suffix
            core = core[:-1]

        if not core:
            return word  # No word to translate

        # Lookup translation
        translated = replacements.get(core.lower(), core)

        # Restore original capitalization:
        if core.isupper():
            translated = translated.upper()
        elif core[0].isupper():
            translated = translated.capitalize()
        else:
            translated = translated.lower()

        # Return with original punctuation
        return prefix + translated + suffix

    if not replacements:
        return text

    pattern = r'\b\w[\w\'-]*\b'
    return re.sub(pattern, replacer, text)


def convert_text_to_epub(text_paragraphs, output_path, title="Gradual Translation", author="Auto Translator"):
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
    return f"EPUB created at {output_path}"


def gradual_translate_epub(epub_input_path, epub_output_path, max_words=200000):
    pages = extract_text_from_epub(epub_input_path)
    paragraphs = []

    # Split all pages into paragraphs
    for page in pages:
        split_paragraphs = [p.strip() for p in page.split('\n') if p.strip()]
        paragraphs.extend(split_paragraphs)

    translator = Translator()
    translated_words = {}
    seen_words = set()

    i = 0
    while i < len(paragraphs) and len(translated_words) < max_words:
        group = paragraphs[i:i+3]
        all_text = ' '.join(group)
        words = clean_and_tokenize(all_text)
        word_freq = Counter(words)

        # Replace already translated words
        for j in range(i, len(paragraphs)):
            paragraphs[j] = replace_words(paragraphs[j], translated_words)

        # Find next untranslated word
        new_words = [
    w for w, _ in word_freq.most_common()
    if w not in seen_words and not (SOURCE_LANG == 'en' and w.lower() == 'a')
]

        if new_words:
            word_to_translate = new_words[0]
            try:
                translated = translator.translate(word_to_translate, src=SOURCE_LANG, dest=TARGET_LANG).text
                translated_words[word_to_translate] = translated
                seen_words.add(word_to_translate)
                seen_words.add(reverse_first_char_case(word_to_translate))
                seen_words.add(translated)
                seen_words.add(reverse_first_char_case(translated))
                print(word_to_translate, " -> ", translated)

                # Replace newly translated word from current paragraph onward
                for j in range(i, len(paragraphs)):
                    paragraphs[j] = replace_words(paragraphs[j], translated_words)

            except Exception as e:
                print(f"Translation failed for '{word_to_translate}': {e}")

        i += 3

    return convert_text_to_epub(paragraphs, epub_output_path)

# ✅ RUN THIS SECTION
gradual_translate_epub("book.epub", "translated_output.epub", max_words=200000)
