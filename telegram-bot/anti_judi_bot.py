import os
import json
import torch
import logging
import string
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from transformers import BertTokenizer, BertForSequenceClassification
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ChatMemberHandler, ContextTypes, filters

# Konfigurasi logging
logging.basicConfig(
    filename="bot_activity.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Memuat model IndoBERT dan tokenizer
logging.info("Memuat model IndoBERT dan tokenizer...")
tokenizer = BertTokenizer.from_pretrained(CHECKPOINT_PATH)
model = BertForSequenceClassification.from_pretrained(CHECKPOINT_PATH)
model.eval()
logging.info("Model dan tokenizer berhasil dimuat!")

# Fungsi untuk load dan save daftar grup aktif
def load_active_groups():
    try:
        if os.path.exists(ACTIVE_GROUPS_FILE):
            with open(ACTIVE_GROUPS_FILE, "r") as f:
                return json.load(f)  # Memuat sebagai dictionary
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"Gagal memuat {ACTIVE_GROUPS_FILE}: {e}")
    return {}

def save_active_groups(groups):
    formatted_groups = {
        str(chat_id): {
            "group_name": dt.get("group_name", ""),
            "activated_by": dt.get("activated_by"),
            "date": dt["date"],
            "time": dt["time"],
            "admins": dt.get("admins", [])  # Simpan daftar admin sebagai list of dict
        } for chat_id, dt in groups.items()
    }
    try:
        with open(ACTIVE_GROUPS_FILE, "w") as f:
            json.dump(formatted_groups, f, indent=4)
    except OSError as e:
        logging.error(f"Gagal menyimpan {ACTIVE_GROUPS_FILE}: {e}")

# Fungsi untuk load dan save daftar pengguna yang telah diblokir
def load_banned_users():
    try:
        if os.path.exists(BAN_FILE):
            with open(BAN_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"Gagal memuat {BAN_FILE}: {e}")
    return {}

def save_banned_users(banned_users):
    formatted_banned_users = {
        str(user_id): {
            "username": dt.get("username", ""),
            "name": dt.get("name", ""),
            "date": dt["date"],
            "time": dt["time"]
        } for user_id, dt in banned_users.items()
    }
    try:
        with open(BAN_FILE, "w") as f:
            json.dump(formatted_banned_users, f, indent=4)
    except OSError as e:
        logging.error(f"Gagal menyimpan {BAN_FILE}: {e}")

# Fungsi untuk load dan save daftar user pribadi
def load_users():
    try:
        if os.path.exists(USER_FILE):
            with open(USER_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"Gagal memuat {USER_FILE}: {e}")
    return {}

def save_users(users):
    formatted_users = {
        str(user_id): {
            "username": dt.get("username", ""),
            "name": dt.get("name", ""),
            "date": dt["date"],
            "time": dt["time"]
        } for user_id, dt in users.items()
    }
    try:
        with open(USER_FILE, "w") as f:
            json.dump(formatted_users, f, indent=4)
    except OSError as e:
        logging.error(f"Gagal menyimpan {USER_FILE}: {e}")

# Fungsi untuk load dan save daftar non pelanggaran
def load_non_violations():
    try:
        if os.path.exists(NON_VIOLATION_FILE):
            with open(NON_VIOLATION_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"Gagal memuat {NON_VIOLATION_FILE}: {e}")
    return {}

def save_non_violations(non_violations):
    formatted_non_violations = {
        str(user_id): [
            {
                "username": entry.get("username", ""),
                "name": entry.get("name", ""),
                "group_id": entry.get("group_id", ""),
                "group_name": entry.get("group_name", ""),
                "timestamp": entry.get("timestamp", ""),
                "message": entry.get("message", ""),
                "message_id": entry.get("message_id", None)
            }
            for entry in entries
        ]
        for user_id, entries in non_violations.items()
    }
    try:
        with open(NON_VIOLATION_FILE, "w") as f:
            json.dump(formatted_non_violations, f, indent=4)
    except OSError as e:
        logging.error(f"Gagal menyimpan {NON_VIOLATION_FILE}: {e}")

# Fungsi untuk load dan save daftar pelanggaran
def load_violations():
    try:
        if os.path.exists(VIOLATION_FILE):
            with open(VIOLATION_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"Gagal memuat {VIOLATION_FILE}: {e}")
    return {}

def save_violations(violations):
    formatted_violations = {
        str(user_id): [
            {
                "username": entry.get("username", ""),
                "name": entry.get("name", ""),
                "group_id": entry.get("group_id", ""),
                "group_name": entry.get("group_name", ""),
                "timestamp": entry.get("timestamp", ""),
                "message": entry.get("message", ""),
                "message_id": entry.get("message_id", None)
            }
            for entry in entries
        ]
        for user_id, entries in violations.items()
    }
    try:
        with open(VIOLATION_FILE, "w") as f:
            json.dump(formatted_violations, f, indent=4)
    except OSError as e:
        logging.error(f"Gagal menyimpan {VIOLATION_FILE}: {e}")

# Fungsi untuk load dan save daftar mute
def load_mute_tracker():
    try:
        if os.path.exists(MUTE_TRACKER_FILE):
            with open(MUTE_TRACKER_FILE, "r") as f:
                raw = json.load(f)
                return {
                    str(user_id): {
                        "username": data.get("username", ""),
                        "name": data.get("name", ""),
                        "until": datetime.fromisoformat(data["until"]),
                        "groups": data.get("groups", {})
                    }
                    for user_id, data in raw.items()
                }
    except (json.JSONDecodeError, OSError, ValueError) as e:
        logging.warning(f"Gagal memuat {MUTE_TRACKER_FILE}: {e}")
    return {}

def save_mute_tracker(mute_tracker):
    try:
        formatted_mute_tracker = {
            str(user_id): {
                "username": data.get("username", ""),
                "name": data.get("name", ""),
                "until": data["until"].replace(microsecond=0).isoformat(),
                "groups": data.get("groups", {})
            }
            for user_id, data in mute_tracker.items()
        }
        with open(MUTE_TRACKER_FILE, "w") as f:
            json.dump(formatted_mute_tracker, f, indent=4)
    except OSError as e:
        logging.error(f"Gagal menyimpan {MUTE_TRACKER_FILE}: {e}")

# Load data saat bot start
users_started = load_users()
active_groups = load_active_groups()
non_violations = load_non_violations()
violations = load_violations()
mute_tracker = load_mute_tracker()
banned_users = load_banned_users()
# Struktur penyimpanan data untuk pelanggaran
violation_tracker = defaultdict(int)
for user_id, entries in violations.items():
    violation_tracker[user_id] = len(entries)

# Fungsi untuk melakukan prediksi apakah pesan mengandung promosi judi
def predict_judi(text):
    logging.info(f"Memprediksi pesan: {text}")
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1).squeeze()
    predicted_label = probabilities.argmax().item()
    logging.info(f"Hasil prediksi: {predicted_label}")
    return predicted_label

# Fungsi filter pesan
def is_valid_for_prediction(text):
    if not text:
        return False
    text = text.strip()
    if len(text) < 5:
        return False
    if text.isdigit():
        return False
    if all(char in string.punctuation for char in text):
        return False
    if len(text.split()) == 1 and len(text) <= 5:
        return False
    return True

# Fungsi untuk mengecek apakah pengguna adalah admin atau owner
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ["administrator", "creator"]  # Pakai string langsung
    except Exception as e:
        logging.error(f"Error saat mengecek admin: {str(e)}")
        return False

# Fungsi cek user 
async def is_user_in_group(bot, group_id: int, user_id: int) -> bool:
    try:
        member: ChatMember = await bot.get_chat_member(chat_id=group_id, user_id=user_id)
        return member.status in ["member", "administrator", "creator", "restricted"]
    except TelegramError as e:
        logging.warning(f"[is_user_in_group] Gagal getChatMember: {e}")
    except Exception as e:
        logging.error(f"[is_user_in_group] Exception: {e}")
    return False

# Handler untuk perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.message.chat.type
    bot_username = context.bot.username
    user = update.message.from_user
    user_id = str(update.effective_user.id) # Mengubah chat_id menjadi string agar sesuai dengan format dict
    user_name = f"@{user.username}" if user.username else user.first_name or "Pengguna"
    args = context.args  # untuk handle parameter start=verifikasi

    # Start dari Chat Pribadi (dengan /start verifikasi)
    if chat_type == "private" and args and args[0] == "verifikasi":
        if user_id not in users_started:
            now = datetime.now()
            users_started[user_id] = {
                "username": user_name,
                "name": user.full_name or "",
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S")
            }
            save_users(users_started)
            logging.info(f"User verifikasi berhasil dicatat: {user_id} - {user_name}")
        else:
            logging.info(f"User sudah pernah verifikasi sebelumnya: {user_id} - {user_name}")

        await update.message.reply_text(
            "✅ Verifikasi berhasil - Anda telah terverifikasi dan dapat berinteraksi di grup seperti biasa!"
        )

        # Unrestrict user di semua grup aktif
        for group_id in active_groups:
            try:
                member = await context.bot.get_chat_member(chat_id=int(group_id), user_id=int(user_id))
                if member.status in ["restricted", "member"]:
                    await context.bot.restrict_chat_member(
                        chat_id=int(group_id),
                        user_id=int(user_id),
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_audios=True,
                            can_send_documents=True,
                            can_send_photos=True,
                            can_send_videos=True,
                            can_send_video_notes=True,
                            can_send_voice_notes=True,
                            can_send_polls=True,
                            can_send_other_messages=True,
                            can_add_web_page_previews=True,
                            can_invite_users=True
                        )
                    )
                    logging.info(f"✅ {user_name} (ID: {user_id}) di-unrestrict di grup {group_id}")
            except Exception as e:
                logging.warning(f"Gagal unrestrict user {user_id} di grup {group_id}: {e}")
        return

    # Start dari Chat Pribadi (tanpa argumen verifikasi)
    if chat_type == "private":
        keyboard = [
            [InlineKeyboardButton("➕ Tambahkan AntiJudiBot ke dalam Grup", url=f"https://t.me/{bot_username}?startgroup=true")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Halo {user_name}! Saya AntiJudiBot! 👋🏻\n\n"
            "Saya adalah bot untuk melindungi grup Anda dari pesan promosi judi online!\n\n"
            "Fitur Utama:\n"
            "- Deteksi & hapus otomatis pesan promosi judi online.\n"
            "- Peringatan dan mute otomatis bagi pengguna yang melanggar.\n"
            "- Auto-kick & blokir pengguna yang melakukan pelanggaran secara berulang.\n"
            "- Dashboard AntiJudiBot untuk admin grup.\n\n"
            "Klik tombol di bawah untuk menambahkan AntiJudiBot ke dalam grup! ⬇️",
            parse_mode="HTML",
            reply_markup=reply_markup
        )

        # Simpan user
        if user_id not in users_started:
            now = datetime.now()
            users_started[user_id] = {
                "username": user_name,
                "name": user.full_name or "",
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S")
            }
            save_users(users_started)
            logging.info(f"User baru dicatat: {user_id} - {user_name}")
        else:
            logging.info(f"User sudah terdaftar: {user_id} - {user_name}")
        return
    
    # Jika bot di-start menggunakan /start dalam grup
    await update.message.reply_text("🚫 Gunakan /start_antijudibot untuk mengaktifkan AntiJudiBot di dalam grup ini!")

# Handler untuk perintah /start_antijudibot
async def start_anti_judi_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.message.chat.type
    user = update.message.from_user
    chat_id = str(update.effective_chat.id)  # Mengubah chat_id menjadi string agar sesuai dengan format dict
    user_name = f"@{user.username}" if user.username else user.full_name or "Pengguna"

    # Mengabaikan perintah jika diketik di chat pribadi
    if chat_type == "private":
        await update.message.reply_text("🚫 Gunakan /start_antijudibot di dalam grup!")
        return

    # Cek apakah user yang menjalankan perintah adalah admin atau owner
    if not await is_admin(update, context):
        await update.message.reply_text("🚫 Hanya Admin yang dapat mengaktifkan AntiJudiBot di dalam grup ini!")
        return

    # Cek bot sudah menjadi admin
    bot_id = context.bot.id
    bot_member = await context.bot.get_chat_member(chat_id=int(chat_id), user_id=bot_id)

    if bot_member.status != ChatMemberStatus.ADMINISTRATOR:
        await update.message.reply_text(
            "⚠️ Bot belum menjadi Admin di dalam grup ini - Pastikan bot telah menjadi Admin dan memiliki izin akses di dalam grup!")
        return

    # Jika sudah aktif sebelumnya
    if chat_id in active_groups:
        await update.message.reply_text("✅ AntiJudiBot telah diaktifkan di dalam grup ini!")
        return

    # Ambil daftar admin grup (termasuk owner)
    try:
        admin_members = await context.bot.get_chat_administrators(chat_id=int(chat_id))
        admin_list = []
        for admin in admin_members:
            admin_user = admin.user
            admin_list.append({
                "user_id": str(admin_user.id),
                "username": f"@{admin_user.username}" if admin_user.username else admin_user.full_name
            })
    except Exception as e:
        logging.error(f"Gagal mengambil daftar admin grup {chat_id}: {e}")
        admin_list = []

    # Set zona waktu WIB
    wib = timezone(timedelta(hours=7))
    now = datetime.now(wib)

    # Simpan aktivasi baru
    active_groups[chat_id] = {
        "group_name": update.effective_chat.title or "",
        "activated_by": user_name,
        "date": now.strftime("%Y-%m-%d"),  # Format: YYYY-MM-DD
        "time": now.strftime("%H:%M:%S") + " WIB",  # Format: HH:MM:SS
        "admins": admin_list
    }
    save_active_groups(active_groups) # Simpan data ke file atau database

    await update.message.reply_text("✅ AntiJudiBot aktif di dalam grup ini!")

    # Kirim pesan verifikasi ke anggota
    bot_username = context.bot.username
    verification_text = (
        "Semua anggota grup harus verifikasi dengan klik tombol di bawah dan tekan tombol START di DM bot!"
    )
    keyboard = [[InlineKeyboardButton("✅ Verifikasi", url=f"https://t.me/{bot_username}?start=verifikasi")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=int(chat_id),
        text=verification_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# Handler untuk perintah /stop_antijudibot
async def stop_anti_judi_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.message.chat.type
    chat_id = str(update.effective_chat.id)  # Mengubah chat_id menjadi string agar sesuai dengan format dict

    # Mengabaikan perintah jika diketik di chat pribadi
    if chat_type == "private":
        await update.message.reply_text("🚫 Gunakan /stop_antijudibot di dalam grup!")
        return

    # Cek apakah user yang menjalankan perintah adalah admin atau owner
    if not await is_admin(update, context):
        await update.message.reply_text("🚫 Hanya Admin yang dapat menonaktifkan AntiJudiBot di dalam grup ini!")
        return

    if chat_id not in active_groups:
        await update.message.reply_text("⚠️ AntiJudiBot belum aktif di dalam grup ini!")
        return

    # Menghapus grup dari daftar active_groups
    active_groups.pop(chat_id, None)  # Menggunakan pop agar tidak error jika key tidak ditemukan
    save_active_groups(active_groups)

    await update.message.reply_text("⛔ AntiJudiBot dinonaktifkan di dalam grup ini!")

# Handler untuk perintah /status_antijudibot
async def status_anti_judi_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.message.chat.type
    chat_id = str(update.effective_chat.id)  # Ubah chat_id menjadi string agar cocok dengan dict

    # Mengabaikan perintah jika diketik di chat pribadi
    if chat_type == "private":
        await update.message.reply_text("🚫 Gunakan /status_antijudibot di dalam grup!")
        return
    
    # Cek apakah user yang menjalankan perintah adalah admin atau owner
    if not await is_admin(update, context):
        await update.message.reply_text("🚫 Hanya Admin yang dapat mengecek status AntiJudiBot di dalam grup ini!")
        return

    if chat_id in active_groups:
        status_message = (
            "✅ AntiJudiBot aktif di dalam grup ini!\n\n"
            f"_Aktivasi oleh : {active_groups[chat_id]['activated_by']}_\n"
            f"_Tanggal Aktivasi : {active_groups[chat_id]['date']}_\n"
            f"_Jam Aktivasi : {active_groups[chat_id]['time']}_\n"
        )
    else:
        status_message = "⚠️ AntiJudiBot tidak aktif di dalam grup ini!"

    await update.message.reply_text(status_message, parse_mode="Markdown")

# Handler untuk menangani pesan masuk
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.message.chat.type
    text = update.message.text
    user = update.message.from_user
    chat_id = str(update.effective_chat.id)  # Mengubah chat_id menjadi string agar sesuai dengan format dict
    user_id = str(update.effective_user.id)  # Mengubah user_id menjadi string agar sesuai dengan format dict
    user_name = f"@{user.username}" if user.username else user.first_name or "Pengguna"
    group_name = update.effective_chat.title or ""
    message_id = update.message.message_id
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Jika pesan dikirim di chat pribadi
    if chat_type == "private":
        return

    # Abaikan jika bot belum diaktifkan di grup
    if chat_id not in active_groups:
        return

    # Abaikan pesan yang tidak layak diproses
    if not is_valid_for_prediction(text):
        logging.info(f"[FILTERED] Pesan tidak layak diproses dari {user_name}: {text}")
        return

    logging.info(f"Menerima pesan dari {user_name} (ID: {user_id}): {text}")

    # Jika terdeteksi promosi judi
    if predict_judi(text) == 1:
        # Cek apakah sudah dikoreksi sebagai bersih → jangan masukkan ke violations
        for log in non_violations.get(user_id, []):
            if log["message_id"] == message_id:
                return
            
        logging.warning(f"{user_name} (ID: {user_id}) mengirimkan pesan promosi judi: {text}")

        # Hapus pesan dan hitung pelanggaran
        await update.message.delete()
        violation_tracker[user_id] += 1

        # Tambahkan ke violations log
        if user_id not in violations:
            violations[user_id] = []

        violations[user_id].append({
            "username": user_name,
            "name": user.full_name or "",
            "group_id": chat_id,
            "group_name": group_name,
            "timestamp": timestamp,
            "message": text,
            "message_id": message_id
        })
        save_violations(violations)

        # 1) Kirim peringatan di grup
        await context.bot.send_message(chat_id=int(chat_id), text=f"⚠️ Peringatan kepada {user_name}, pesan Anda terdeteksi sebagai promosi judi online!")

        # 2) Kirim notifikasi ke DM
        if user_id in users_started:
            try:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=(
                        f"⚠️ Peringatan kepada {user_name}, pesan Anda di dalam grup telah dihapus karena terdeteksi sebagai promosi judi online!"
                    )
                )
                logging.info(f"Notifikasi pelanggaran dikirim ke DM {user_name} (ID: {user_id}).")
            except Exception as e:
                logging.warning(f"Gagal mengirim DM ke {user_name} (ID: {user_id}): {e}")

        # 3) Jika pelanggaran ke-5 → mute
        if violation_tracker[user_id] == 20:
            mute_until = datetime.now() + timedelta(hours=6)
            until_timestamp = int(mute_until.timestamp())  # Konversi ke Unix timestamp (detik)

            # Inisialisasi data mute user
            if user_id not in mute_tracker:
                mute_tracker[user_id] = {
                    "username": user_name,
                    "name": user.full_name or "",
                    "until": mute_until,
                    "groups": {}
                }
            else:
                mute_tracker[user_id]["until"] = mute_until  # update durasi jika perlu

            berhasil_mute = []

            for group_id, group_info in active_groups.items():
                if await is_user_in_group(context.bot, int(group_id), int(user_id)):
                    try:
                        await context.bot.restrict_chat_member(
                            chat_id=int(group_id),
                            user_id=int(user_id),
                            permissions=ChatPermissions(
                                can_send_messages=False,
                                can_send_audios=False,
                                can_send_documents=False,
                                can_send_photos=False,
                                can_send_videos=False,
                                can_send_video_notes=False,
                                can_send_voice_notes=False,
                                can_send_polls=False,
                                can_send_other_messages=False,
                                can_add_web_page_previews=False,
                                can_invite_users=False
                            ),
                            until_date=until_timestamp
                        )

                        # Simpan info grup yang berhasil mute
                        mute_tracker[user_id]["groups"][str(group_id)] = {
                            "group_name": group_info["group_name"]
                        }
                        berhasil_mute.append(group_info["group_name"])

                        # Kirim notifikasi ke grup
                        await context.bot.send_message(
                            chat_id=int(group_id),
                            text=f"🔇 {user_name} dimute karena pelanggaran berulang!"
                        )

                    except Exception as e:
                        logging.warning(f"Gagal mute {user_name} di grup {group_info['group_name']}: {e}")

            if berhasil_mute:
                save_mute_tracker(mute_tracker)
                logging.warning(f"{user_name} dimute di {len(berhasil_mute)} grup: {', '.join(berhasil_mute)}.")

                # Kirim notifikasi ke DM
                if user_id in users_started and berhasil_mute:
                    try:
                        await context.bot.send_message(
                            chat_id=int(user_id),
                            text="🔇 Anda telah dimute karena pelanggaran berulang di semua grup!\n\n"
                        )
                        logging.info(f"DM mute berhasil dikirim ke {user_name} (ID: {user_id}).")
                    except Exception as e:
                        logging.warning(f"Gagal kirim DM mute ke {user_name}: {e}")
            else:
                logging.info(f"Tidak ada grup yang memproses mute untuk {user_name}.")

        # 4) Jika pelanggaran >5 → ban
        elif violation_tracker[user_id] > 20:
            berhasil_ban = []

            for group_id, group_info in active_groups.items():
                if await is_user_in_group(context.bot, int(group_id), int(user_id)):
                    try:
                        await context.bot.ban_chat_member(
                            chat_id=int(group_id),
                            user_id=int(user_id)
                        )
                        berhasil_ban.append(group_info["group_name"])

                        # Kirim notifikasi ke grup
                        await context.bot.send_message(
                            chat_id=int(group_id),
                            text=f"🚫 {user_name} dikeluarkan dan diblokir dari grup karena pelanggaran berulang kali!"
                        )

                    except Exception as e:
                        logging.warning(f"Gagal ban {user_name} dari grup {group_info['group_name']}: {e}")

            # Simpan ke data banned users
            if berhasil_ban:
                banned_users[user_id] = {
                    "username": user_name,
                    "name": user.full_name or "",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "time": datetime.now().strftime("%H:%M:%S")
                }
                save_banned_users(banned_users)
                logging.warning(f"{user_name} telah diblokir dari {', '.join(berhasil_ban)}.")

                # Kirim notifikasi ke DM (hanya sekali)
                if user_id in users_started:
                    try:
                        await context.bot.send_message(
                            chat_id=int(user_id),
                            text="🚫 Anda telah dikeluarkan dan diblokir dari semua grup karena pelanggaran berulang kali!"
                        )
                        logging.info(f"Notifikasi ban berhasil dikirim ke DM {user_name} (ID: {user_id})")
                    except Exception as e:
                        logging.warning(f"Gagal kirim DM ban ke {user_name}: {e}")
            else:
                logging.warning(f"Tidak berhasil ban {user_name} di grup manapun.")
    else:
        # Cek apakah sudah dikoreksi sebagai pelanggaran → jangan simpan ke non_violations
        for log in violations.get(user_id, []):
            if log["message_id"] == message_id:
                return
            
        # Simpan pesan yang tidak melanggar ke dalam non_violations.json
        if user_id not in non_violations:
            non_violations[user_id] = []

        non_violations[user_id].append({
            "username": user_name,
            "name": user.full_name or "",
            "group_id": chat_id,
            "group_name": group_name,
            "timestamp": timestamp,
            "message": text,
            "message_id": message_id
        })
        save_non_violations(non_violations)

# Handler untuk cek user dimute dan waktunya sudah selesai (unmute otomatis)
async def auto_unmute_users(context: ContextTypes.DEFAULT_TYPE):
    global mute_tracker
    # Reload mute_tracker dari file setiap kali handler dipanggil
    with open("mute_tracker.json") as f:
        raw = json.load(f)
        # Convert kembali nilai "until" jadi datetime
        mute_tracker = {
            uid: {
                **data,
                "until": datetime.fromisoformat(data["until"])
            } for uid, data in raw.items()
        }

    now = datetime.now()
    updated = False

    for user_id, data in list(mute_tracker.items()):
        try:
            mute_until = data["until"]
            if isinstance(mute_until, str):
                mute_until = datetime.fromisoformat(mute_until)

            if now >= mute_until:
                berhasil_unmute = []

                for group_id, group_info in data.get("groups", {}).items():
                    try:
                        await context.bot.restrict_chat_member(
                            chat_id=int(group_id),
                            user_id=int(user_id),
                            permissions=ChatPermissions(
                                can_send_messages=True,
                                can_send_audios=True,
                                can_send_documents=True,
                                can_send_photos=True,
                                can_send_videos=True,
                                can_send_video_notes=True,
                                can_send_voice_notes=True,
                                can_send_polls=True,
                                can_send_other_messages=True,
                                can_add_web_page_previews=True,
                                can_invite_users=True
                            )
                        )

                        # Kirim notifikasi ke grup
                        await context.bot.send_message(
                            chat_id=int(group_id),
                            text=f"🔊 {data['username']} telah di unmute karena durasi mute user sudah berakhir!"
                        )
                        logging.info(f"User {user_id} unmute otomatis di grup {group_info['group_name']}")

                        berhasil_unmute.append(group_info["group_name"])

                    except Exception as e:
                        logging.error(f"Gagal unmute {user_id} di grup {group_id}: {e}")

                # DM dikirim sekali saja jika berhasil unmute di grup manapun
                if berhasil_unmute and user_id in users_started:
                    try:
                        await context.bot.send_message(
                            chat_id=int(user_id),
                            text="🔊 Durasi mute Anda telah berakhir, sekarang Anda dapat mengirim pesan lagi di semua grup!"
                        )
                        logging.info(f"DM unmute berhasil dikirim ke {data['username']} (ID: {user_id})")
                    except Exception as e:
                        logging.warning(f"Gagal kirim DM ke {data['username']}: {e}")

                # Hapus dari mute tracker
                del mute_tracker[user_id]
                updated = True

        except Exception as e:
            logging.error(f"Gagal memproses unmute otomatis untuk user {user_id}: {e}")

    if updated:
        save_mute_tracker(mute_tracker)

# Handler untuk bot yang baru ditambahkan ke grup
async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(update.effective_chat.id)  # ID grup
    my_chat_member = update.my_chat_member   # Data status bot di grup

    if not my_chat_member:
        logging.warning(f"Tidak ada data 'my_chat_member' untuk update di grup {chat_id}.")
        return

    old_status = my_chat_member.old_chat_member.status
    new_status = my_chat_member.new_chat_member.status

    logging.info(f"Bot status di chat {chat_id} berubah dari {old_status} menjadi {new_status}.")

    # Saat bot ditambahkan ke grup atau diangkat jadi admin
    if chat.type in ["group", "supergroup"] \
       and old_status in ["left", "kicked"] \
       and new_status in ["member", "administrator"]:

        logging.info(f"Bot telah ditambahkan ke grup {chat_id}, mengirim welcome message.")

        # Pesan sambutan untuk semua member & daftar perintah admin
        welcome_text = (
            "Halo semua! Saya AntiJudiBot! 👋🏻\n\n"
            "Saya akan membantu mendeteksi dan menghapus pesan promosi judi online di dalam grup ini.\n\n"
            "Admin Commands:\n"
            "- /start_antijudibot - Aktifkan bot di grup\n"
            "- /stop_antijudibot - Nonaktifkan bot di grup\n"
            "- /status_antijudibot - Cek status bot di grup\n\n"
            "Pastikan saya telah menjadi Admin dan memiliki izin akses di dalam grup! ✅"
        )

        # Kirim pesan
        await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_text,
            parse_mode="HTML"
        )

# Handler untuk anggota grup baru
async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member = update.chat_member  # Mengambil informasi perubahan status anggota
    chat_id = str(update.effective_chat.id)  # ID grup

    if not chat_member:
        logging.warning(f"Tidak ada data 'chat_member' untuk update di grup {chat_id}.")
        return

    user = chat_member.new_chat_member.user
    user_id = str(user.id)
    user_name = f"@{user.username}" if user.username else user.first_name or "Pengguna"
    new_status = chat_member.new_chat_member.status

    # Abaikan jika bot yang bergabung
    if user.is_bot:
        logging.info(f"Bot {user_name} bergabung ke grup {chat_id}, diabaikan.")
        return

    # Log setiap perubahan status anggota
    logging.info(f"Status Anggota Grup: Pengguna {user_name} (ID: {user_id}) Grup {chat_id} - Status: {new_status}")

    # Cek apakah bot masih aktif di grup ini sebelum mengambil tindakan
    if chat_id not in active_groups:
        logging.info(f"Bot tidak aktif di grup {chat_id}. Mengabaikan event!")
        return

    # Jika pengguna baru bergabung (baik secara manual atau diundang admin/member)
    if new_status in ["member", "administrator"]:
        # Periksa apakah user ini ada di daftar blokir
        if user_id in banned_users:
            logging.warning(f"Pengguna {user_name} (ID: {user_id}) bergabung kembali ke dalam grup. Pengguna akan dikeluarkan!")
            try:
                # Keluarkan pengguna dari grup
                await context.bot.ban_chat_member(chat_id=int(chat_id), user_id=int(user_id))
                await context.bot.send_message(chat_id=int(chat_id), text=f"🚫 {user_name} telah diblokir karena pelanggaran dan tidak diperbolehkan untuk bergabung ke dalam grup!")
                logging.info(f"Pengguna {user_name} (ID: {user_id}) berhasil dikeluarkan dari grup {chat_id}!")

                # Notifikasi ban di DM
                if user_id in banned_users:  # user_id dalam bentuk string
                    try:
                        await context.bot.send_message(
                            chat_id=int(user_id),
                            text="🚫 Anda telah diblokir karena pelanggaran dan tidak diperbolehkan untuk bergabung ke dalam grup!"
                        )
                        logging.info(f"Notifikasi ban berhasil dikirim ke {user_name} (ID: {user_id})")
                    except Exception as e:
                        logging.warning(f"Gagal kirim DM ban ke {user_name} (ID: {user_id}): {e}")

            except Exception as e:
                logging.error(f"Gagal mengeluarkan {user_name} dari grup {chat_id}: {str(e)}")
            return
        
        # Jika user belum pernah /start
        if user_id not in users_started:
            logging.info(f"User {user_name} (ID: {user_id}) belum pernah /start. Akan direstrict dan dikirim pesan.")

            # 1. Restrict user sepenuhnya
            try:
                await context.bot.restrict_chat_member(
                    chat_id=int(chat_id),
                    user_id=int(user_id),
                    permissions=ChatPermissions(
                        can_send_messages=False,
                        can_send_audios=False,
                        can_send_documents=False,
                        can_send_photos=False,
                        can_send_videos=False,
                        can_send_video_notes=False,
                        can_send_voice_notes=False,
                        can_send_polls=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                        can_invite_users=False
                    )
                )
                logging.info(f"{user_name} (ID: {user_id}) berhasil direstrict di grup {chat_id}")
            except Exception as e:
                logging.warning(f"Gagal restrict user {user_name} di grup {chat_id}: {e}")

            # 2. Kirim pesan sambutan dengan tombol ke grup
            welcome_text = (
                f"Halo {user_name}! Selamat datang!  👋🏻\n\n"
                "Saya AntiJudiBot yang akan membantu menjaga grup ini dari pesan promosi judi online.\n\n"
                "Silakan verifikasi dengan klik tombol di bawah dan tekan tombol START di DM bot agar dapat mengirim pesan!"
            )
            keyboard = [
                [InlineKeyboardButton("✅ Verifikasi", url=f"https://t.me/{context.bot.username}?start=verifikasi")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await context.bot.send_message(
                    chat_id=int(chat_id),
                    text=welcome_text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                logging.info(f"Pesan sambutan dikirim ke grup {chat_id} untuk {user_name}")
            except Exception as e:
                logging.warning(f"Gagal kirim pesan sambutan ke {user_name} di grup {chat_id}: {e}")

# Fungsi utama untuk menjalankan bot
def main():
    logging.info("Memulai bot...")
    
    # Membangun aplikasi dengan token
    application = ApplicationBuilder().token(TOKEN).build()

    # Menambahkan handler untuk perintah dan pesan
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_antijudibot", start_anti_judi_bot))
    application.add_handler(CommandHandler("stop_antijudibot", stop_anti_judi_bot))
    application.add_handler(CommandHandler("status_antijudibot", status_anti_judi_bot))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.job_queue.run_repeating(auto_unmute_users, interval=60, first=10)
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    logging.info("Bot sedang berjalan...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)  # Memastikan semua jenis update diterima

if __name__ == "__main__":
    main()
