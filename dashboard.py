import streamlit as st
import json
import pandas as pd
import plotly.express as px
import requests
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from st_aggrid import AgGrid, GridOptionsBuilder
from telegram import Bot
import asyncio
from telegram.constants import ParseMode
import re
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# Fungsi Cek User
def is_user_in_group(group_id, user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {
        "chat_id": group_id,
        "user_id": user_id
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            status = response.json()["result"]["status"]
            return status in ["member", "administrator", "creator", "restricted"]
        else:
            print(f"[DEBUG] Gagal getChatMember: {response.status_code} {response.text}")
    except Exception as e:
        print(f"[DEBUG] Exception getChatMember: {e}")
    return False

# Fungsi mute user
def mute_user_telegram(user_id, group_id, until_timestamp):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/restrictChatMember"
    payload = {
        "chat_id": group_id,
        "user_id": user_id,
        "permissions": {
            "can_send_messages": False,
            "can_send_audios": False,
            "can_send_documents": False,
            "can_send_photos": False,
            "can_send_videos": False,
            "can_send_video_notes": False,
            "can_send_voice_notes": False,
            "can_send_polls": False,
            "can_send_other_messages": False,
            "can_add_web_page_previews": False,
            "can_invite_users": False
        },
        "until_date": until_timestamp
    }
    response = requests.post(url, json=payload)
    return response.status_code == 200

# Fungsi ban user
def ban_user_telegram(user_id, group_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/banChatMember"
    payload = {
        "chat_id": group_id,
        "user_id": user_id
    }
    response = requests.post(url, json=payload)
    return response.status_code == 200

# Fungsi unmute user
def unmute_user_telegram(user_id, group_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/restrictChatMember"
    payload = {
        "chat_id": group_id,
        "user_id": user_id,
        "permissions": {
            "can_send_messages": True,
            "can_send_audios": True,
            "can_send_documents": True,
            "can_send_photos": True,
            "can_send_videos": True,
            "can_send_video_notes": True,
            "can_send_voice_notes": True,
            "can_send_polls": True,
            "can_send_other_messages": True,
            "can_add_web_page_previews": True,
            "can_invite_users": True
        }
    }
    response = requests.post(url, json=payload)
    return response.status_code == 200

# Fungsi unban user
def unban_user_telegram(user_id, group_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/unbanChatMember"
    payload = {
        "chat_id": group_id,
        "user_id": user_id,
        "only_if_banned": True
    }
    response = requests.post(url, json=payload)
    return response.status_code == 200

# Fungsi kirim pesan
def kirim_pesan_telegram(user_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": user_id, 
        "text": message
    }
    response = requests.post(url, json=payload)
    return response.status_code == 200

# Fungsi kirim notifikasi grup
def kirim_notifikasi_grup(group_id, text, parse_mode=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": group_id,
        "text": text
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    response = requests.post(url, json=payload)
    return response.status_code == 200

# Fungsi kirim notifikasi dm
def kirim_dm(user_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": user_id,
        "text": text
    }
    response = requests.post(url, json=payload)
    return response.status_code == 200

# Fungsi load file JSON
def load_json(file):
    with open(file, "r") as f:
        return json.load(f)

# Load semua data
violations = load_json("violations.json")
non_violations = load_json("non_violations.json")
mute_data = load_json("mute_tracker.json")
ban_data = load_json("banned_users.json")
active_groups = load_json("active_groups.json")
user_started = load_json("user_started.json")

# Inisialisasi waktu pertama kali jika belum ada
if "last_update_time" not in st.session_state:
    st.session_state["last_update_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Sidebar
with st.sidebar:
    st.title("📊 Dashboard AntiJudiBot")

    # Tombol perbarui data
    if st.button("🔄 Perbarui Data"):
        with st.spinner("Memuat ulang data..."):
            st.session_state["last_update_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state["selected_tab"] = "📈 Statistik"  # Reset ke tab Statistik
            st.rerun()

    # Tampilkan waktu terakhir diperbarui dengan tampilan terpisah
    st.markdown("**🕒 Terakhir diperbarui:**")
    st.markdown(f"{st.session_state['last_update_time']}")

    # Tab pemilihan
    tab = st.radio(
    "Pilih Tab",
    ["📈 Statistik", "📄 Pesan & Pelanggaran", "⛔ Mute & Ban"],
    index=["📈 Statistik", "📄 Pesan & Pelanggaran", "⛔ Mute & Ban"].index(
        st.session_state.get("selected_tab", "📈 Statistik")
    ),
    key="selected_tab"
    )

# Tab statistik dashboard
if tab == "📈 Statistik":
    st.title("📈 Statistik AntiJudiBot")

    st.markdown("<br>", unsafe_allow_html=True)

    # Metrik ringkas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Grup Aktif", len(active_groups))
    with col2:
        total_violations = sum([len(v) for v in violations.values()])
        st.metric("Total Pelanggaran", total_violations)
    with col3:
        st.metric("Total User Mute", len(mute_data))
    with col4:
        st.metric("Total User Banned", len(ban_data))

    st.divider()

    # Pie chart
    st.subheader("📌 Persentase Pelanggaran Grup")
    group_counts = defaultdict(int)
    for user_id, logs in violations.items():
        for v in logs:
            group_counts[v['group_name']] += 1
    pie_df = pd.DataFrame(group_counts.items(), columns=["Grup", "Jumlah"])
    fig_pie = px.pie(pie_df, names='Grup', values='Jumlah', hole=0.4)
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_pie, use_container_width=True)

    # Histogram pelanggaran
    st.subheader("📊 Grafik Jumlah Pelanggaran Grup")
    df_number = []
    for user_id, logs in violations.items():
        for v in logs:
            date = v['timestamp'].split()[0]
            df_number.append({
                "Tanggal": date,
                "Grup": v['group_name']
            })
    df_number = pd.DataFrame(df_number)
    filter_grup_jumlah = st.multiselect(
        "Filter Grup (Jumlah Pelanggaran)",
        options=df_number["Grup"].unique(),
        default=df_number["Grup"].unique(),
        key="jumlah_pelanggaran_filter"
    )
    df_filtered_jumlah = df_number[df_number["Grup"].isin(filter_grup_jumlah)]
    fig_number = px.histogram(df_filtered_jumlah, x="Tanggal", color="Grup", barmode="group")
    fig_number.update_layout(xaxis_title="Tanggal", yaxis_title="Jumlah Pelanggaran")
    st.plotly_chart(fig_number, use_container_width=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)

    # Grafik tren pelanggaran
    st.subheader("📈 Grafik Tren Pelanggaran Grup")
    df_trend = []
    for user_id, logs in violations.items():
        for v in logs:
            date = v['timestamp'].split()[0]
            df_trend.append({
                "Tanggal": date,
                "Grup": v['group_name']
            })
    df_trend = pd.DataFrame(df_trend)
    filter_grup_tren = st.multiselect(
        "Filter Grup (Tren Pelanggaran)",
        options=df_trend["Grup"].unique(),
        default=df_trend["Grup"].unique(),
        key="tren_pelanggaran_filter"
    )
    df_filtered_tren = df_trend[df_trend["Grup"].isin(filter_grup_tren)]
    trend_df = df_filtered_tren.groupby(["Tanggal", "Grup"]).size().reset_index(name="Jumlah")
    fig_trend = px.line(trend_df, x="Tanggal", y="Jumlah", color="Grup")
    fig_trend.update_layout(xaxis_title="Tanggal", yaxis_title="Jumlah Pelanggaran")
    st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Heatmap
    st.subheader("🔥 Heatmap Pelanggaran")
    df_heatmap = []
    for user_id, logs in violations.items():
        for v in logs:
            date = v['timestamp'].split()[0]
            df_heatmap.append({
                "Tanggal": date,
                "Grup": v['group_name']
            })
    df_heatmap = pd.DataFrame(df_heatmap)

    # Multiselect untuk filter grup khusus heatmap
    filter_grup_heatmap = st.multiselect(
        "Filter Grup (Heatmap)",
        options=df_heatmap["Grup"].unique(),
        default=df_heatmap["Grup"].unique(),
        key="heatmap_filter"
    )
    df_filtered_heatmap = df_heatmap[df_heatmap["Grup"].isin(filter_grup_heatmap)]
    heatmap_df = df_filtered_heatmap.groupby(["Grup", "Tanggal"]).size().reset_index(name='Jumlah')
    heatmap_pivot = heatmap_df.pivot(index='Grup', columns='Tanggal', values='Jumlah').fillna(0)
    fig_heatmap = px.imshow(
        heatmap_pivot,
        text_auto=True,
        aspect="equal",
        color_continuous_scale="Reds"
    )
    fig_heatmap.update_layout(xaxis_title="Tanggal", yaxis_title="Grup")
    st.plotly_chart(fig_heatmap, use_container_width=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # WordCloud
    st.subheader("☁️ WordCloud Pesan Pelanggaran")
    # Ambil semua nama grup dari data pelanggaran
    all_group_names = sorted(set(v["group_name"] for logs in violations.values() for v in logs))
    # Multiselect untuk memilih grup
    selected_groups_wc = st.multiselect(
        "Filter Grup (WordCloud)",
        options=all_group_names,
        default=all_group_names,
        key="wordcloud_group_filter"
    )
    # Gabungkan pesan dari grup yang dipilih
    filtered_texts = [
        log["message"]
        for logs in violations.values()
        for log in logs
        if log["group_name"] in selected_groups_wc
    ]
    # Gabungkan jadi satu teks besar
    combined_text = " ".join(filtered_texts)
    # Bersihkan kata-kata 1 huruf (misalnya: "x", "m", "d", dll)
    cleaned_text = " ".join(word for word in re.findall(r'\b\w+\b', combined_text) if len(word) > 1 and word.isalpha())
    # Hanya tampilkan WordCloud jika ada teks
    if cleaned_text.strip():
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            colormap='cool'
        ).generate(cleaned_text)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis("off")
        st.pyplot(fig)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # Tabel verifikasi
    st.subheader("✅ Users Terverifikasi (/start Bot)")
    verified_df = pd.DataFrame.from_dict(user_started, orient="index").reset_index()
    verified_df.columns = ["User ID", "Username", "Name", "Date", "Time"]
    # Parsing date asli ke datetime
    verified_df["Date_raw"] = pd.to_datetime(verified_df["Date"]).dt.date
    # Simpan versi string untuk tampilan
    verified_df["Date"] = verified_df["Date_raw"].astype(str)
    # Tampilkan metrik total
    col1, col2 = st.columns(2)
    col1.metric("Total Users Terverifikasi", len(verified_df))
    col2.metric("User Baru Hari Ini", (verified_df["Date_raw"] == datetime.now().date()).sum())

    # Jumlah user per hari
    summary_df = verified_df.groupby("Date").size().reset_index(name="Jumlah User")
    fig_summary = px.bar(summary_df, x="Date", y="Jumlah User")
    fig_summary.update_layout(xaxis_title="Tanggal", yaxis_title="Jumlah User")
    st.plotly_chart(fig_summary, use_container_width=True)

    # Data users
    st.markdown("#### 📋 Data Users")
    display_df = verified_df.drop(columns=["Date_raw"])
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_default_column(sortable=True, filter=True, resizable=True)
    gridOptions = gb.build()
    AgGrid(display_df, gridOptions=gridOptions, fit_columns_on_grid_load=True)

# Tab pesan & pelanggaran dashboard 
elif tab == "📄 Pesan & Pelanggaran":
    st.title("📄 Pesan & Pelanggaran Users")

    st.markdown("<br>", unsafe_allow_html=True)

    # Notifikasi
    if st.session_state.get("notif_hapus_pelanggaran"):
        st.success(st.session_state["notif_hapus_pelanggaran"])
        del st.session_state["notif_hapus_pelanggaran"]

    if st.session_state.get("notif_deteksi_pelanggaran"):
        st.success(st.session_state["notif_deteksi_pelanggaran"])
        del st.session_state["notif_deteksi_pelanggaran"]

    if st.session_state.get("notif_mute_user"):
        st.success(st.session_state["notif_mute_user"])
        del st.session_state["notif_mute_user"]

    if st.session_state.get("notif_ban_user"):
        st.success(st.session_state["notif_ban_user"])
        del st.session_state["notif_ban_user"]
    
    # Tabel data pesan users
    st.subheader("📊 Data Pesan Users")

    combined_data = []

    for user_id in set(list(violations.keys()) + list(non_violations.keys())):
        vio_logs = violations.get(user_id, [])
        non_vio_logs = non_violations.get(user_id, [])

        group_ids = set([entry["group_id"] for entry in vio_logs + non_vio_logs])

        for group_id in group_ids:
            vio_in_group = [v for v in vio_logs if v["group_id"] == group_id]
            non_vio_in_group = [v for v in non_vio_logs if v["group_id"] == group_id]

            # Cek data referensi
            if vio_in_group:
                ref_entry = vio_in_group[0]
            elif non_vio_in_group:
                ref_entry = non_vio_in_group[0]
            else:
                continue  # tidak ada data yang valid, skip

            combined_data.append({
                "User ID": user_id,
                "Username": ref_entry.get("username", ""),
                "Name": ref_entry.get("name", ""),
                "Grup": ref_entry.get("group_name", f"ID: {group_id}"),
                "Total": len(vio_in_group) + len(non_vio_in_group),
                "Bersih": len(non_vio_in_group),
                "Melanggar": len(vio_in_group)
            })

    df_activity = pd.DataFrame(combined_data)

    if not df_activity.empty:
        gb = GridOptionsBuilder.from_dataframe(df_activity)
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_default_column(sortable=True, filter=True, resizable=True)
        gridOptions = gb.build()
        AgGrid(df_activity, gridOptions=gridOptions, fit_columns_on_grid_load=True)
    else:
        st.info("❌ Belum ada data pesan dari users!")

    st.divider()
    
    # Tabel daftar pesan & pelanggaran users
    st.subheader("📝 Daftar Pesan & Pelanggaran Users")

    # Gabungkan semua user_id dari violations dan non_violations
    all_user_ids = set(violations.keys()) | set(non_violations.keys())

    all_data = []
    for user_id in all_user_ids:
        # Ambil data terakhir dari violations atau non_violations
        last_violation = violations.get(user_id, [])
        last_clean = non_violations.get(user_id, [])

        latest_log = None
        if last_violation:
            latest_log = sorted(last_violation, key=lambda x: x["timestamp"])[-1]
        elif last_clean:
            latest_log = sorted(last_clean, key=lambda x: x["timestamp"])[-1]

        if latest_log:
            latest_log["user_id"] = user_id
            all_data.append(latest_log)

    if not all_data:
        st.info("❌ Tidak ada data users tercatat!")
    else:
        df = pd.DataFrame(all_data)

        # Filter grup
        grup_filter = st.selectbox("Filter Grup", options=["Semua"] + df["group_name"].unique().tolist())
        if grup_filter != "Semua":
            df = df[df["group_name"] == grup_filter]

        # Filter tanggal
        tanggal_unik = sorted(
            set(
                ts["timestamp"].split()[0]
                for uid in all_user_ids
                for ts in (violations.get(uid, []) + non_violations.get(uid, []))
            )
        )
        tanggal_filter = st.selectbox("Filter Tanggal", options=["Semua"] + tanggal_unik)
        if tanggal_filter != "Semua":
            df = df[df["timestamp"].str.startswith(tanggal_filter)]

        # Filter pencarian
        search_query = st.text_input("Cari berdasarkan Username / Nama / User ID", placeholder="Ketik Username, Nama, atau User ID").lower().strip()
        if search_query:
            df = df[
                df["username"].str.lower().str.contains(search_query, na=False) |
                df["name"].str.lower().str.contains(search_query, na=False) |
                df["user_id"].astype(str).str.contains(search_query)
            ]

        if df.empty:
            st.info("❌ Tidak ada data users pada filter yang dipilih!")
        else:
            for _, row in df.iterrows():
                user_id = row["user_id"]
                
                # Ambil data
                clean_logs = non_violations.get(user_id, [])
                full_logs = violations.get(user_id, [])
                total_clean = len(clean_logs)
                total_violations = len(full_logs)
                
                # Judul expander
                expander_title = (
                    f"{row['name']} ({row['username']}) - {row['timestamp']} - "
                    f"✅ {total_clean} | ⚠️ {total_violations}"
                )

                with st.expander(expander_title):
                    selected_clean_indexes = []
                    selected_indexes = []

                    # Pesan bersih
                    if clean_logs:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.write(f"✅ Pesan Bersih : {total_clean}")
                        for idx, cl in enumerate(clean_logs):
                            checkbox_label = f"`{cl['timestamp']} - {cl['group_name']}`: {cl['message']}"
                            checked = st.checkbox(
                                checkbox_label,
                                key=f"checkbox_clean_{user_id}_{idx}"
                            )
                            if checked:
                                selected_clean_indexes.append(idx)
                    else:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.write(f"✅ Pesan Bersih : {total_clean}")

                    st.divider()

                    # Pesan pelanggaran
                    if full_logs:
                        st.write(f"⚠️ Pesan Melanggar : {total_violations}")
                        for idx, log in enumerate(full_logs):
                            checkbox_label = f"`{log['timestamp']} - {log['group_name']}`: {log['message']}"
                            checked = st.checkbox(
                                checkbox_label,
                                key=f"checkbox_{user_id}_{idx}"
                            )
                            if checked:
                                selected_indexes.append(idx)
                    else:
                        st.write(f"⚠️ Pesan Melanggar : {total_violations}")

                    # Notifikasi kirim pesan
                    notif_key = f"notif_pesan_pelanggaran_{user_id}"
                    if notif_key in st.session_state:
                        if st.session_state[notif_key] == "success":
                            st.success("✅ Pesan berhasil dikirim!")
                        elif st.session_state[notif_key] == "failed":
                            st.error("❌ Gagal mengirim pesan!")
                        del st.session_state[notif_key]

                    st.markdown("<br>", unsafe_allow_html=True)

                    col1, col2, col3, col4, col5 = st.columns([1.25, 1.3, 1.5, 1.2, 0.82])
                    with col1:
                        # Tombol kirim pesan
                        if st.button("📩 Pesan", key=f"tulis_pesan_pelanggaran_{user_id}"):
                            st.session_state[f"show_pesan_pelanggaran_{user_id}"] = not st.session_state.get(f"show_pesan_pelanggaran_{user_id}", False)

                        if st.session_state.get(f"show_pesan_pelanggaran_{user_id}", False):
                            pesan = st.text_area(label="Tulis Pesan", placeholder="Tulis Pesan", label_visibility="collapsed", key=f"pesan_pelanggaran_{user_id}")
                            if st.button("Kirim", key=f"kirim_pelanggaran_{user_id}"):
                                if kirim_pesan_telegram(user_id, pesan):
                                    st.session_state[notif_key] = "success"
                                else:
                                    st.session_state[notif_key] = "failed"
                                st.session_state[f"show_pesan_pelanggaran_{user_id}"] = False
                                st.rerun()

                    with col2:
                        # Tombol hapus pelanggaran
                        if st.button("✅ Bersih", key=f"hapus_{user_id}"):
                            if selected_indexes:
                                # Pindahkan hanya pelanggaran yang dipilih
                                moved_vio = [log for idx, log in enumerate(full_logs) if idx in selected_indexes]
                                violations[user_id] = [
                                    log for idx, log in enumerate(full_logs) if idx not in selected_indexes
                                ]
                                if not violations[user_id]:
                                    violations.pop(user_id, None)
                                pesan_dipindah = f"{len(selected_indexes)} pesan melanggar dipindahkan ke pesan bersih"
                            else:
                                # Pindahkan semua pelanggaran
                                moved_vio = full_logs
                                violations.pop(user_id, None)
                                pesan_dipindah = "Semua pesan melanggar dipindahkan ke pesan bersih"

                            # Tambahkan ke non_violations
                            if moved_vio:
                                if user_id not in non_violations:
                                    non_violations[user_id] = []
                                non_violations[user_id].extend(moved_vio)

                                # Kirim ulang pesan dihapus ke grup
                                for log in moved_vio:
                                    group_id = log.get("group_id")
                                    text = log.get("message")

                                    # Kirim notifikasi ke grup
                                    if group_id and text:
                                        try:
                                            kirim_notifikasi_grup(
                                                group_id,
                                                f"✅ Pesan dari {row['username']} telah dihapus dari daftar pelanggaran oleh Admin!\n\n_Pesan : {text}_",
                                                parse_mode=ParseMode.MARKDOWN
                                            )
                                        except Exception as e:
                                            print(f"Gagal kirim ulang pesan ke grup {group_id}: {e}")

                            # Simpan perubahan
                            with open("violations.json", "w") as f:
                                json.dump(violations, f, indent=4)
                            with open("non_violations.json", "w") as f:
                                json.dump(non_violations, f, indent=4)

                            # Kirim DM jika user sudah pernah start bot
                            if user_id in user_started:
                                try:
                                    kirim_dm(user_id, "✅ Pesan Anda telah dihapus dari daftar pelanggaran oleh Admin karena tidak termasuk promosi judi online!")
                                except Exception as e:
                                    print(f"Gagal kirim DM ke {user_id}: {e}")

                            st.session_state["notif_hapus_pelanggaran"] = f"✅ {pesan_dipindah} dari {row['name']} ({row['username']})!"
                            st.rerun()

                    with col3:
                        # Tombol deteksi pelanggaran
                        if st.button("❌ Melanggar", key=f"deteksi_{user_id}"):
                            if selected_clean_indexes:
                                # Pindahkan hanya pesan bersih yang dipilih
                                moved_clean = [log for idx, log in enumerate(clean_logs) if idx in selected_clean_indexes]
                                non_violations[user_id] = [
                                    log for idx, log in enumerate(clean_logs) if idx not in selected_clean_indexes
                                ]
                                if not non_violations[user_id]:
                                    non_violations.pop(user_id, None)
                                pesan_dipindah = f"{len(selected_clean_indexes)} pesan bersih dipindahkan ke pesan melanggar"
                            else:
                                # Pindahkan semua pesan bersih
                                moved_clean = clean_logs
                                non_violations.pop(user_id, None)
                                pesan_dipindah = "Semua pesan bersih dipindahkan ke pesan melanggar"

                            # Tambahkan ke violations
                            if moved_clean:
                                if user_id not in violations:
                                    violations[user_id] = []
                                violations[user_id].extend(moved_clean)

                                # Hapus pesan dari grup & kirim notifikasi ke grup
                                async def proses_pesan_melanggar():
                                    for log in moved_clean:
                                        group_id = log.get("group_id")
                                        message_id = log.get("message_id")

                                        # Hapus pesan dari grup
                                        if group_id and message_id:
                                            try:
                                                await bot.delete_message(chat_id=group_id, message_id=int(message_id))
                                            except Exception as e:
                                                print(f"Gagal menghapus pesan di grup {group_id}: {e}")

                                        # Kirim notifikasi ke grup
                                        if group_id:
                                            try:
                                                kirim_notifikasi_grup(
                                                    group_id,
                                                    f"⚠️ Pesan dari {row['username']} telah dihapus oleh Admin karena termasuk promosi judi online!"
                                                )
                                            except Exception as e:
                                                print(f"Gagal kirim notifikasi ke grup {group_id}: {e}")

                                try:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    loop.run_until_complete(proses_pesan_melanggar())
                                    loop.close()
                                except RuntimeError as e:
                                    print(f"Loop error: {e}")

                            # Simpan perubahan
                            with open("violations.json", "w") as f:
                                json.dump(violations, f, indent=4)
                            with open("non_violations.json", "w") as f:
                                json.dump(non_violations, f, indent=4)

                            # Kirim DM ke user (jika sudah start bot)
                            if user_id in user_started:
                                try:
                                    kirim_dm(user_id, "⚠️ Pesan Anda di dalam grup telah dihapus oleh Admin karena termasuk promosi judi online!")
                                except Exception as e:
                                    print(f"Gagal kirim DM ke {user_id}: {e}")

                            st.session_state["notif_deteksi_pelanggaran"] = f"✅ {pesan_dipindah} dari {row['name']} ({row['username']})!"
                            st.rerun()
                    
                    with col4:
                        # Tombol mute user
                        if st.button("🔇 Mute", key=f"mute_{user_id}"):
                            mute_until = datetime.now() + timedelta(hours=6)
                            until_timestamp = int(mute_until.timestamp())
                            berhasil = []

                            # Inisialisasi data jika user belum ada
                            if user_id not in mute_data:
                                mute_data[user_id] = {
                                    "username": row["username"],
                                    "name": row["name"],
                                    "until": mute_until,
                                    "groups": {}
                                }
                            else:
                                mute_data[user_id]["until"] = mute_until  # update durasi
                                if "groups" not in mute_data[user_id]:
                                    mute_data[user_id]["groups"] = {}

                            for group_id, group_info in active_groups.items():
                                # Cek apakah user masih tergabung
                                if is_user_in_group(group_id, user_id):
                                    try:
                                        success = mute_user_telegram(user_id, group_id, until_timestamp)
                                        if success:
                                            berhasil.append(group_info["group_name"])

                                            # Simpan grup yang berhasil dimute
                                            mute_data[user_id]["groups"][str(group_id)] = {
                                                "group_name": group_info["group_name"]
                                            }

                                            # Kirim notifikasi ke grup
                                            kirim_notifikasi_grup(
                                                group_id,
                                                f"🔇 {row['username']} dimute oleh Admin karena melakukan promosi judi online berulang kali!"
                                            )

                                    except Exception as e:
                                        print(f"Gagal mute user di grup {group_id}: {e}")

                            # Simpan file JSON dengan format ISO string
                            if berhasil:
                                with open("mute_tracker.json", "w") as f:
                                    formatted = {
                                        uid: {
                                            **data,
                                            "until": data["until"].replace(microsecond=0).isoformat()
                                        } for uid, data in mute_data.items()
                                    }
                                    json.dump(formatted, f, indent=4)

                                # Kirim DM jika mute berhasil
                                if user_id in user_started:
                                    try:
                                        kirim_dm(
                                            user_id,
                                            "🔇 Anda telah dimute oleh Admin di semua grup karena melakukan promosi judi online berulang kali!"
                                        )
                                    except Exception as e:
                                        print(f"Gagal kirim DM mute ke {user_id}: {e}")

                                st.session_state["notif_mute_user"] = f"🔇 {row['name']} ({row['username']}) berhasil dimute di semua grup! ({', '.join(berhasil)})"
                            else:
                                st.session_state["notif_mute_user"] = f"❌ Gagal mute user {row['name']}!"
                                
                            st.rerun()

                    with col5:
                        # Tombol ban user
                        if st.button("🚫 Ban", key=f"ban_{user_id}"):
                            berhasil = []

                            for group_id, group_info in active_groups.items():
                                # Cek apakah user masih di grup
                                if is_user_in_group(group_id, user_id):
                                    try:
                                        success = ban_user_telegram(user_id, group_id)
                                        if success:
                                            berhasil.append(group_info["group_name"])

                                            # Kirim notifikasi ke grup
                                            kirim_notifikasi_grup(
                                                group_id,
                                                f"🚫 {row['username']} dikeluarkan dan diblokir oleh Admin karena melakukan promosi judi online berulang kali!"
                                            )

                                    except Exception as e:
                                        print(f"Gagal ban user di grup {group_id}: {e}")

                            if berhasil:
                                # Simpan ke file banned_users.json
                                ban_data[user_id] = {
                                    "username": row["username"],
                                    "name": row["name"],
                                    "date": datetime.now().strftime("%Y-%m-%d"),
                                    "time": datetime.now().strftime("%H:%M:%S")
                                }
                                with open("banned_users.json", "w") as f:
                                    json.dump(ban_data, f, indent=4)

                                # Kirim DM ke user (satu kali saja)
                                if user_id in user_started:
                                    try:
                                        kirim_dm(
                                            user_id,
                                            "🚫 Anda telah dikeluarkan dan diblokir oleh Admin di semua grup karena melakukan promosi judi online berulang kali!"
                                        )
                                    except Exception as e:
                                        print(f"Gagal kirim DM ban ke {user_id}: {e}")

                                st.session_state["notif_ban_user"] = f"🚫 {row['name']} ({row['username']}) berhasil diban di semua grup! ({', '.join(berhasil)})"
                            else:
                                st.session_state["notif_ban_user"] = f"❌ Gagal ban user {row['name']}!"
                            
                            st.rerun()

# Tab Mute dan Ban Dashboard
elif tab == "⛔ Mute & Ban":
    st.title("⛔ Mute & Ban Users")

    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("🔇 Daftar Mute Users")

    # Notifikasi unmute
    if st.session_state.get("notif_unmute"):
        st.success(st.session_state["notif_unmute"])
        del st.session_state["notif_unmute"]
    
    if not mute_data:
        st.info("❌ Tidak ada data user di mute!")
    else:
        for user_id, user in mute_data.items():
            with st.expander(f"{user['name']} ({user['username']})"):
                until_str = user['until']
                st.write("⏳ Durasi Mute :", until_str)

                # Tampilkan notifikasi kirim pesan
                notif_key = f"notif_pesan_mute_{user_id}"
                if notif_key in st.session_state:
                    if st.session_state[notif_key] == "success":
                        st.success("✅ Pesan berhasil dikirim!")
                    elif st.session_state[notif_key] == "failed":
                        st.error("❌ Gagal mengirim pesan!")
                    del st.session_state[notif_key]

                st.markdown("<br>", unsafe_allow_html=True)

                col_spacer1, col1, col2, col_spacer2 = st.columns([3, 3, 2, 3])
                with col1:
                    if st.button("📩 Pesan", key=f"tulis_pesan_mute_{user_id}"):
                        st.session_state[f"show_pesan_mute_{user_id}"] = not st.session_state.get(f"show_pesan_mute_{user_id}", False)

                    if st.session_state.get(f"show_pesan_mute_{user_id}", False):
                        pesan = st.text_area(label="Tulis Pesan", placeholder="Tulis Pesan", label_visibility="collapsed", key=f"pesan_pelanggaran_{user_id}")
                        if st.button("Kirim", key=f"kirim_mute_{user_id}"):
                            if kirim_pesan_telegram(user_id, pesan):
                                st.session_state[notif_key] = "success"
                            else:
                                st.session_state[notif_key] = "failed"
                            st.session_state[f"show_pesan_mute_{user_id}"] = False
                            st.rerun()

                with col2:
                    if st.button("🔊 Unmute", key=f"unmute_{user_id}"):
                        berhasil = []

                        for group_id, group_info in active_groups.items():
                            if is_user_in_group(group_id, user_id):
                                try:
                                    success = unmute_user_telegram(user_id, group_id)
                                    if success:
                                        berhasil.append(group_info["group_name"])
                                        kirim_notifikasi_grup(group_id, f"🔊 {user['username']} telah di unmute oleh Admin!")
                                except:
                                    pass

                        # Hapus data dari file mute_tracker.json
                        mute_data.pop(user_id, None)
                        with open("mute_tracker.json", "w") as f:
                            json.dump(mute_data, f, indent=4)

                        # Kirim notifikasi DM hanya sekali setelah semua unmute berhasil
                        if berhasil:
                            if user_id in user_started:
                                try:
                                    kirim_dm(user_id, "🔊 Anda telah di unmute oleh Admin di semua grup!")
                                except:
                                    pass
                            st.session_state["notif_unmute"] = f"✅ {user['name']} ({user['username']}) berhasil di unmute di semua grup! ({', '.join(berhasil)})"
                        else:
                            st.session_state["notif_unmute"] = f"❌ Gagal unmute user {user['name']}!"

                        st.rerun()

    st.divider()
    st.subheader("🚫 Daftar Banned Users")

    # Notifikasi unban
    if st.session_state.get("notif_unban"):
        st.success(st.session_state["notif_unban"])
        del st.session_state["notif_unban"]
    
    if not ban_data:
        st.info("❌ Tidak ada data user di banned!")
    else:
        for user_id, user in ban_data.items():
            with st.expander(f"{user['name']} ({user['username']})"):
                st.write("📅 Tanggal Banned :", user['date'], user['time'])

                # Notifikasi hasil pengiriman pesan
                notif_key = f"notif_pesan_ban_{user_id}"
                if notif_key in st.session_state:
                    if st.session_state[notif_key] == "success":
                        st.success("✅ Pesan berhasil dikirim!")
                    elif st.session_state[notif_key] == "failed":
                        st.error("❌ Gagal mengirim pesan!")
                    del st.session_state[notif_key]

                st.markdown("<br>", unsafe_allow_html=True)

                col_spacer1, col1, col2, col_spacer2 = st.columns([3, 3, 2, 3])
                with col1:
                    if st.button("📩 Pesan", key=f"tulis_pesan_ban_{user_id}"):
                        st.session_state[f"show_pesan_ban_{user_id}"] = not st.session_state.get(f"show_pesan_ban_{user_id}", False)

                    if st.session_state.get(f"show_pesan_ban_{user_id}", False):
                        pesan = st.text_area(label="Tulis Pesan", placeholder="Tulis Pesan", label_visibility="collapsed", key=f"pesan_pelanggaran_{user_id}")
                        if st.button("Kirim", key=f"kirim_ban_{user_id}"):
                            if kirim_pesan_telegram(user_id, pesan):
                                st.session_state[notif_key] = "success"
                            else:
                                st.session_state[notif_key] = "failed"
                            st.session_state[f"show_pesan_ban_{user_id}"] = False
                            st.rerun()

                with col2:
                    if st.button("🔓 Unban", key=f"unban_{user_id}"):
                        berhasil = []

                        for group_id, group_info in active_groups.items():
                            try:
                                success = unban_user_telegram(user_id, group_id)
                                if success:
                                    berhasil.append(group_info["group_name"])
                            except:
                                pass

                        # Kirim DM hanya jika ada keberhasilan unban
                        if berhasil and user_id in user_started:
                            try:
                                kirim_dm(user_id, "🔓 Anda telah di unban (dihapus dari daftar blokir user) oleh Admin dan bisa bergabung kembali ke dalam grup!")
                            except:
                                pass

                        # Hapus data dari file banned_users.json
                        ban_data.pop(user_id, None)
                        with open("banned_users.json", "w") as f:
                            json.dump(ban_data, f, indent=4)

                        if berhasil:
                            st.session_state["notif_unban"] = f"✅ {user['name']} ({user['username']}) berhasil di unban!"
                        else:
                            st.session_state["notif_unban"] = f"❌ Gagal unban user {user['name']}!"
                        st.rerun()
