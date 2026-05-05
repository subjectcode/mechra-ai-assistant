import streamlit as st
import os
import re
import json
from google import genai
from google.genai import types
from groq import Groq
from exa_py import Exa
import random

# Konfigurasi Halaman
st.set_page_config(page_title="MECHRA Smart AI Mechanic", page_icon="🔧", layout="wide")

# CSS Styling
st.markdown("""
<style>
    .stApp { font-family: 'Inter', sans-serif; }
    .stButton > button { border-color: #ff6b00; color: #ff6b00; border-radius: 8px; font-weight: 500; }
    .stButton > button:hover { background-color: #ff6b00; color: white; border-color: #ff6b00; }
    .stButton > button[kind="primary"] { background-color: #ff6b00; color: white; border-color: #ff6b00; font-weight: 600; }
    .stButton > button[kind="primary"]:hover { background-color: #e66000; border-color: #e66000; }

    .sidebar-brand { display: flex; align-items: center; margin-bottom: 5px; }
    .sidebar-brand-icon { font-size: 28px; background-color: #fff3e6; padding: 10px; border-radius: 50%; color: #ff6b00; margin-right: 12px; }
    .sidebar-brand-text { font-size: 22px; font-weight: 700; color: #ff6b00; line-height: 1.1; }
    .sidebar-brand-sub { font-size: 13px; color: #888; font-weight: 500; margin-left: 56px; margin-bottom: 25px; }
    
    .settings-card { border: 1px solid #eaeaea; border-radius: 12px; padding: 20px; margin-bottom: 20px; background-color: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
    .settings-header { display: flex; align-items: center; font-weight: 600; font-size: 16px; margin-bottom: 15px; }
    .settings-header-icon { color: #ff6b00; margin-right: 10px; background-color: #fff3e6; padding: 5px 8px; border-radius: 50%; }
    
    .stChatMessage { border: 1px solid #eaeaea; border-radius: 12px; padding: 15px; margin-bottom: 15px; background-color: #ffffff; }
    [data-testid="stChatMessage"][data-baseweb="block"]:has(> div > div > div > div > div > img[alt="user avatar"]) { background-color: #fff3e6; border-color: #ffebcc; }
    
    .diag-card { border: 1px solid #eaeaea; border-radius: 12px; padding: 20px; background-color: #ffffff; box-shadow: 0 4px 10px rgba(0,0,0,0.04); margin-top: 15px; margin-bottom: 20px;}
    .diag-card h4 { color: #ff6b00; margin-top: 0; border-bottom: 1px solid #f0f0f0; padding-bottom: 10px; }
    
    .context-container { border: 1px solid #eaeaea; border-radius: 12px; padding: 15px; background-color: #ffffff; box-shadow: 0 2px 8px rgba(0,0,0,0.02); margin-top: 20px; margin-bottom: 10px; }
    .row-widget.stButton { margin-bottom: 0px; }
</style>
""", unsafe_allow_html=True)

# Inisialisasi State
if "chats" not in st.session_state:
    # Simpan multi chat riwayat
    st.session_state.chats = [{"id": 1, "title": "Percakapan Baru", "messages": [], "diagnosis": None}]
if "active_chat_idx" not in st.session_state:
    st.session_state.active_chat_idx = 0
if "current_view" not in st.session_state:
    st.session_state.current_view = "chat"
if "vehicle_context" not in st.session_state:
    st.session_state.vehicle_context = {"situation": "Belum Dipilih"}
if "suggestions" not in st.session_state:
    st.session_state.suggestions = []
if "auto_send" not in st.session_state:
    st.session_state.auto_send = None

# Set default settings
if "ai_provider" not in st.session_state:
    st.session_state.ai_provider = "Gemini"
if "ai_model" not in st.session_state:
    st.session_state.ai_model = "gemini-3-flash-preview"
if "use_internet" not in st.session_state:
    st.session_state.use_internet = False
    
# Shortcut referensi ke active chat
active_chat = st.session_state.chats[st.session_state.active_chat_idx]

# Fungsi Bantuan
def baca_pengetahuan(query):
    try:
        with open("knowledge.md", "r") as f:
            teks = f.read()
        bagian = teks.split("##")
        kata_kunci = query.lower().split()
        hasil = []
        for b in bagian:
            for k in kata_kunci:
                if len(k) > 3 and k in b.lower():
                    hasil.append("##" + b)
                    break
        return "\n".join(hasil[:2])
    except:
        return ""

def cari_internet(query, api_key):
    try:
        exa = Exa(api_key=api_key)
        res = exa.search_and_contents(query + " masalah mobil otomotif perbaikan", num_results=2, text=True)
        return "\n".join([f"- {r.title}: {r.text[:200]}" for r in res.results])
    except:
        return ""

# Sidebar UI
with st.sidebar:
    st.markdown("""
    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
            <div class="sidebar-brand">
                <span class="sidebar-brand-icon">🔧</span>
                <span class="sidebar-brand-text">MECHRA</span>
            </div>
            <div class="sidebar-brand-sub">Smart AI Mechanic</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("➕ Chat Baru", use_container_width=True, type="primary"):
        # Cegah spam "Percakapan Baru" jika chat teratas masih kosong
        if len(st.session_state.chats) > 0 and len(st.session_state.chats[0]["messages"]) == 0:
            st.session_state.active_chat_idx = 0
            st.session_state.current_view = "chat"
        else:
            new_id = random.randint(100, 99999)
            st.session_state.chats.insert(0, {"id": new_id, "title": "Percakapan Baru", "messages": [], "diagnosis": None})
            st.session_state.active_chat_idx = 0
            st.session_state.suggestions = []
            st.session_state.current_view = "chat"
        st.rerun()
        
    st.markdown("<br><p style='color:#888; font-size:14px; font-weight:600;'>Riwayat Chat</p>", unsafe_allow_html=True)
    
    # Render daftar chat dengan tombol Hapus
    for idx, c in enumerate(st.session_state.chats):
        cols = st.columns([5, 1])
        btn_text = f"💬 {c['title']}"
        
        with cols[0]:
            if idx == st.session_state.active_chat_idx and st.session_state.current_view == "chat":
                st.markdown(f"<div style='color:#ff6b00; font-weight:bold; background-color:#fff3e6; padding:8px; border-radius:5px; margin-bottom:5px; font-size:14px;'>{btn_text}</div>", unsafe_allow_html=True)
            else:
                if st.button(btn_text, key=f"chat_{c['id']}", use_container_width=True):
                    st.session_state.active_chat_idx = idx
                    st.session_state.current_view = "chat"
                    st.session_state.suggestions = []
                    st.rerun()
        with cols[1]:
            if st.button("🗑️", key=f"del_{c['id']}", help="Hapus percakapan"):
                st.session_state.chats.pop(idx)
                if len(st.session_state.chats) == 0:
                    st.session_state.chats = [{"id": 1, "title": "Percakapan Baru", "messages": [], "diagnosis": None}]
                st.session_state.active_chat_idx = 0
                st.rerun()
                
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("⚙️ Pengaturan", use_container_width=True, type="secondary"):
        st.session_state.current_view = "settings"

# --- Tampilan Settings ---
if st.session_state.current_view == "settings":
    st.header("Pengaturan")
    st.warning("⚠️ **Peringatan:** Me-refresh halaman browser (F5) akan mereset semua data karena ini aplikasi Streamlit lokal. Gunakan tombol 'Simpan' dan navigasi bawaan aplikasi.")
    
    st.markdown("<div class='settings-card'>", unsafe_allow_html=True)
    st.markdown("<div class='settings-header'><span class='settings-header-icon'>🔑</span> Konfigurasi API & Model</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        ai_pilihan = st.selectbox("Pilih Provider AI", ["Gemini", "Groq"], index=0 if st.session_state.ai_provider=="Gemini" else 1)
        if ai_pilihan == "Gemini":
            idx = 0 if st.session_state.ai_model == "gemini-3-flash-preview" else 1
            model_opsi = st.selectbox("Pilih Model Gemini", ["gemini-3-flash-preview", "gemini-2.5-flash"], index=idx)
        else:
            model_opsi = st.text_input("Pilih Model Groq", value=st.session_state.get("ai_model_groq", "llama-3.1-8b-instant"))
            
    with col2:
        if ai_pilihan == "Gemini":
            gemini_input = st.text_input("API Key (Gemini)", type="password", value=st.session_state.get("gemini_key_input", ""))
            groq_input = st.session_state.get("groq_key_input", "")
        else:
            groq_input = st.text_input("API Key (Groq)", type="password", value=st.session_state.get("groq_key_input", ""))
            gemini_input = st.session_state.get("gemini_key_input", "")
            
    exa_input = st.text_input("Exa API Key (Untuk Internet)", type="password", value=st.session_state.get("exa_key_input", ""))
    
    if st.button("💾 Simpan Pengaturan API", type="primary"):
        st.session_state.ai_provider = ai_pilihan
        st.session_state.ai_model = model_opsi
        if ai_pilihan == "Groq":
            st.session_state.ai_model_groq = model_opsi
        st.session_state.gemini_key_input = gemini_input
        st.session_state.groq_key_input = groq_input
        st.session_state.exa_key_input = exa_input
        st.success("Pengaturan API Berhasil Disimpan!")
        
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='settings-card'>", unsafe_allow_html=True)
    st.markdown("<div class='settings-header'><span class='settings-header-icon'>⚙️</span> Preferensi</div>", unsafe_allow_html=True)
    pakai_internet = st.toggle("Aktifkan pencarian internet (Exa)", value=st.session_state.use_internet)
    if st.button("💾 Simpan Preferensi", type="primary"):
        st.session_state.use_internet = pakai_internet
        st.success("Preferensi Berhasil Disimpan!")
    st.markdown("</div>", unsafe_allow_html=True)

# --- Tampilan Chat Utama ---
else:
    # Context Selection di atas chat
    st.markdown("<div class='context-container'>", unsafe_allow_html=True)
    st.markdown("<span style='color:#ff6b00; margin-right:10px;'>✨</span> Untuk membantu lebih baik, pilih situasi Anda:", unsafe_allow_html=True)
    scol1, scol2, scol3, scol4 = st.columns(4)
    with scol1:
        if st.button("⚠️ Di Jalan", use_container_width=True, type="primary" if st.session_state.vehicle_context["situation"] == "Di Jalan" else "secondary"):
            st.session_state.vehicle_context["situation"] = "Di Jalan"
            st.rerun()
    with scol2:
        if st.button("🏠 Di Rumah", use_container_width=True, type="primary" if st.session_state.vehicle_context["situation"] == "Di Rumah" else "secondary"):
            st.session_state.vehicle_context["situation"] = "Di Rumah"
            st.rerun()
    with scol3:
        if st.button("🔧 Punya Alat", use_container_width=True, type="primary" if st.session_state.vehicle_context["situation"] == "Punya Alat" else "secondary"):
            st.session_state.vehicle_context["situation"] = "Punya Alat"
            st.rerun()
    with scol4:
        if st.button("🚫 Tanpa Alat", use_container_width=True, type="primary" if st.session_state.vehicle_context["situation"] == "Tanpa Alat" else "secondary"):
            st.session_state.vehicle_context["situation"] = "Tanpa Alat"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if not active_chat["messages"]:
        with st.chat_message("assistant", avatar="🔧"):
            st.write(f"Halo! Saya MECHRA, asisten mekanik AI Anda.\n\nAda yang bisa saya bantu terkait kendaraan Anda hari ini?")

    # Tampilkan History
    for msg in active_chat["messages"]:
        av = "🔧" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=av):
            st.markdown(msg["content"])

    # Tampilkan Diagnosis Card kalau ada
    if active_chat["diagnosis"]:
        d = active_chat["diagnosis"]
        warna_risiko = "#28a745" if d.get('risk_level') == "Low" else "#ffc107" if d.get('risk_level') == "Medium" else "#dc3545"
        st.markdown(f"""
        <div class="diag-card">
            <h4>📋 Kartu Diagnosis</h4>
            <p><b>Tingkat Risiko:</b> <span style='color:{warna_risiko}; font-weight:bold;'>{d.get('risk_level', 'Tidak Diketahui')}</span></p>
            <p><b>Sistem Suspek:</b> {d.get('system', 'Tidak Diketahui')}</p>
            <p><b>Aman Dikendarai:</b> {d.get('safe_to_drive', 'Tidak Diketahui')}</p>
            <p><b>Saran Tindakan:</b> {d.get('recommended_action', '-')}</p>
        </div>
        """, unsafe_allow_html=True)
        
    # Tampilkan rekomendasi tindakan SETELAH asisten membalas
    if st.session_state.suggestions and len(active_chat["messages"]) > 0 and active_chat["messages"][-1]["role"] == "assistant":
        st.write("✨ **Saran Pertanyaan / Tindakan Selanjutnya:**")
        cols = st.columns(len(st.session_state.suggestions))
        for idx, sug in enumerate(st.session_state.suggestions):
            with cols[idx]:
                if st.button(sug, use_container_width=True, key=f"sug_{idx}"):
                    st.session_state.auto_send = sug
                    st.session_state.suggestions = []
                    st.rerun()

    # Input User
    user_input = st.chat_input("Tanyakan apa saja tentang kendaraan Anda...")
    
    if st.session_state.auto_send:
        user_input = st.session_state.auto_send
        st.session_state.auto_send = None

    if user_input:
        st.session_state.suggestions = []
        
        # Ubah judul chat jika ini adalah pesan pertama
        if len(active_chat["messages"]) == 0:
            active_chat["title"] = user_input[:20] + "..." if len(user_input) > 20 else user_input
            
        active_chat["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.write(user_input)
            
        with st.chat_message("assistant", avatar="🔧"):
            loading = st.empty()
            
            ai_model_active = st.session_state.ai_model if st.session_state.ai_provider == "Gemini" else st.session_state.get("ai_model_groq", "llama-3.1-8b-instant")
            loading.write(f"Menganalisis menggunakan {ai_model_active}...")
            
            rag_context = baca_pengetahuan(user_input)
            internet_context = ""
            
            # Prioritaskan API Key dari Form Settings, fallback ke Secrets Colab
            gemini_key = st.session_state.get('gemini_key_input') or os.getenv("GEMINI_API_KEY")
            groq_key = st.session_state.get('groq_key_input') or os.getenv("GROQ_API_KEY")
            exa_key = st.session_state.get('exa_key_input') or os.getenv("EXA_API_KEY")
            
            if st.session_state.use_internet and exa_key:
                internet_context = cari_internet(user_input, exa_key)
                
            situasi = st.session_state.vehicle_context['situation']
            prompt_sistem = f"""
Kamu MECHRA, asisten mekanik AI. Jawab dalam bahasa Indonesia yang ramah dan profesional.

PENTING: User saat ini berada di kondisi "{situasi}". 
Sesuaikan saranmu SECARA SPESIFIK dengan kondisi ini!
- Jika "Di Jalan": Utamakan keselamatan, darurat, menepi, atau panggil derek.
- Jika "Di Rumah": Sarankan pengecekan mandiri yang aman.
- Jika "Punya Alat": Berikan langkah teknis ringan yang bisa dilakukan dengan alat dasar.
- Jika "Tanpa Alat": Jangan sarankan bongkar-bongkar, fokus pada inspeksi visual atau panggil teknisi.

Pengetahuan RAG: {rag_context}
Data Internet: {internet_context}

Format responmu:
1. Sapa ramah. Analisis masalah sesuai kondisi ({situasi}).
2. Kasih saran. JANGAN overclaim.
3. Wajib bikin JSON untuk diagnosis card (jangan sampai lupa):
```json
{{
  "risk_level": "Low" | "Medium" | "High",
  "system": "Engine/Battery/Brake/AC/Electrical/Etc",
  "safe_to_drive": "Yes/No/Not Recommended",
  "recommended_action": "Saran singkat sesuai kondisi"
}}
```
4. Setelah JSON, wajib buat JSON array berisi 2-3 ide pertanyaan follow-up untuk user (sebagai referensi) dengan format:
```suggestions
["Apa kemungkinan penyebab terburuknya?", "Berapa estimasi biaya perbaikan?"]
```
"""

            jawaban_ai = ""
            try:
                if st.session_state.ai_provider == "Gemini" and gemini_key:
                    client = genai.Client(api_key=gemini_key)
                    config = types.GenerateContentConfig(system_instruction=prompt_sistem, temperature=0.7)
                    
                    histori = []
                    for m in active_chat["messages"][:-1]:
                        r = 'user' if m['role'] == 'user' else 'model'
                        histori.append(types.Content(role=r, parts=[types.Part.from_text(text=m['content'])]))
                    
                    chat = client.chats.create(model=ai_model_active, config=config, history=histori)
                    resp = chat.send_message(user_input)
                    jawaban_ai = resp.text
                elif st.session_state.ai_provider == "Groq" and groq_key:
                    client = Groq(api_key=groq_key)
                    
                    messages_groq = [{"role": "system", "content": prompt_sistem}]
                    for m in active_chat["messages"]:
                        messages_groq.append(m)
                        
                    resp = client.chat.completions.create(
                        messages=messages_groq,
                        model=ai_model_active, temperature=0.7
                    )
                    jawaban_ai = resp.choices[0].message.content
                else:
                    jawaban_ai = "Maaf, API Key belum dikonfigurasi di Pengaturan atau Colab Secrets."
                    
            except Exception as e:
                jawaban_ai = f"Error saat memanggil AI: {e}"
                
            # Parse JSON
            teks_bersih = jawaban_ai
            data_diag = None
            cari_json = re.search(r'```json\s*(\{.*?\})\s*```', teks_bersih, re.DOTALL)
            if cari_json:
                try:
                    data_diag = json.loads(cari_json.group(1))
                    teks_bersih = re.sub(r'```json\s*\{.*?\}\s*```', '', teks_bersih, flags=re.DOTALL)
                except:
                    pass
                    
            sug_list = []
            cari_sug = re.search(r'```suggestions\s*(\[.*?\])\s*```', teks_bersih, re.DOTALL)
            if cari_sug:
                try:
                    sug_list = json.loads(cari_sug.group(1))
                    teks_bersih = re.sub(r'```suggestions\s*\[.*?\]\s*```', '', teks_bersih, flags=re.DOTALL)
                except:
                    pass
            
            if not sug_list:
                sug_list = ["Berapa estimasi biayanya?", "Apakah saya bisa perbaiki sendiri?"]
                
            teks_bersih = teks_bersih.strip()
            
            loading.empty()
            st.write(teks_bersih)
            active_chat["messages"].append({"role": "assistant", "content": teks_bersih})
            
            st.session_state.suggestions = sug_list[:3]
            if data_diag:
                active_chat["diagnosis"] = data_diag
                
            st.rerun()
