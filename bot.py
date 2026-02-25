import os
import asyncio
import logging
import re

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from yt_dlp import YoutubeDL

# ================== BOT SOZLAMALARI ==================
TOKEN = "8621085913:AAEvGa6fTiB9fNp61Du3KVdVhW_InkvRWW8"
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================== YORDAMCHI FUNKSIYALAR ==================

def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)


def download_media(url, title, mode='audio'):
    safe_title = clean_filename(title)[:50]

    if mode == 'audio':
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': f"{safe_title}.%(ext)s",
            'quiet': True,
            'noplaylist': True,
        }
    else:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': f"{safe_title}.%(ext)s",
            'quiet': True,
            'noplaylist': True,
        }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


# ================== START ==================

@dp.message(Command("start"))
async def start(message: types.Message):
    start_text = (
        f"<b>🌟 Salom, {message.from_user.first_name}!</b>\n\n"
        "🔍 Musiqa nomini yozing.\n"
        "🚀 <i>Men uni sizga yuklab beraman!</i>"
    )
    await message.answer(start_text, parse_mode="HTML")


# ================== XABAR QABUL QILISH ==================

@dp.message(F.text)
async def handle_message(message: types.Message):
    text = message.text

    if "youtube.com" in text or "youtu.be" in text:
        await download_from_link(message)

    elif "http" in text:
        await message.answer("❌ Hozircha faqat YouTube havolalari qo'llab-quvvatlanadi.")

    else:
        await perform_search(message, text, 1)


# ================== QIDIRUV + PAGINATION ==================

async def perform_search(event, query, page=1):
    msg = event.message if isinstance(event, types.CallbackQuery) else event

    per_page = 10
    max_results = 50

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"ytsearch{max_results}:{query}",
                download=False
            )

        all_results = info.get("entries", [])
        total_count = len(all_results)

        if total_count == 0:
            await msg.answer("❌ Hech narsa topilmadi.")
            return

        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        results = all_results[start_index:end_index]

        kb = InlineKeyboardBuilder()

        list_text = (
            f"<b>🔍 Qidiruv:</b> {query}\n"
            f"<b>📊 Jami topildi:</b> {total_count} ta\n"
            f"────────────────────\n"
        )

        for i, res in enumerate(results, start_index + 1):
            title = res.get("title", "Nomaʼlum")[:40]
            video_id = res.get("id")
            list_text += f"<b>{i}.</b> {title}\n"
            kb.button(text=f"{i}", callback_data=f"dl_{video_id}")

        nav_buttons = []

        if page > 1:
            nav_buttons.append(
                types.InlineKeyboardButton(
                    text="⬅️ Oldingi 10",
                    callback_data=f"page_{query}_{page-1}"
                )
            )

        if end_index < total_count:
            nav_buttons.append(
                types.InlineKeyboardButton(
                    text="Keyingi 10 ➡️",
                    callback_data=f"page_{query}_{page+1}"
                )
            )

        if nav_buttons:
            kb.row(*nav_buttons)

        kb.adjust(5)

        if isinstance(event, types.CallbackQuery):
            await event.message.edit_text(
                list_text,
                reply_markup=kb.as_markup(),
                parse_mode="HTML"
            )
        else:
            await event.answer(
                list_text,
                reply_markup=kb.as_markup(),
                parse_mode="HTML"
            )

    except Exception as e:
        logging.error(e)
        await msg.answer("❌ Qidiruvda xatolik yuz berdi.")


# ================== PAGINATION CALLBACK ==================

@dp.callback_query(F.data.startswith("page_"))
async def pagination_callback(call: types.CallbackQuery):
    parts = call.data.split("_")
    query = parts[1]
    page = int(parts[2])

    await call.answer()
    await perform_search(call, query, page)


# ================== VIDEO LINK YUKLASH ==================

async def download_from_link(message: types.Message):
    status = await message.answer("⏳ Video tahlil qilinmoqda...")
    url = message.text

    try:
        with YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'video_file')

        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, title, 'video')

        video = types.FSInputFile(file_path)

        await message.answer_video(
            video,
            caption=f"🎬 <b>{title}</b>\n\n@DiyorMuzik99_bot",
            parse_mode="HTML"
        )

        await status.delete()

        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        logging.error(e)
        await status.edit_text("❌ Yuklashda xatolik yuz berdi.")


# ================== AUDIO YUKLASH ==================

@dp.callback_query(F.data.startswith("dl_"))
async def download_callback(call: types.CallbackQuery):
    video_id = call.data.split("_")[1]
    url = f"https://www.youtube.com/watch?v={video_id}"

    await call.answer("Yuklash boshlandi...")
    status_msg = await call.message.answer("📥 Tayyorlanmoqda...")

    try:
        with YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'audio_file')

        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, title, 'audio')

        audio = types.FSInputFile(file_path)

        await call.message.answer_audio(
            audio,
            caption=f"🎶 <b>{title}</b>\n\n@DiyorMuzik99_bot",
            parse_mode="HTML"
        )

        await status_msg.delete()

        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        logging.error(e)
        await status_msg.edit_text("❌ Audio yuklashda xatolik.")


# ================== MAIN ==================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi")