import os
import sqlite3
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

st.title("Chatbot Konsultan Perawatan Kulit")

# Initialize SQLite database
def init_db():
    """Inisialisasi database SQLite dan buat tabel produk jika belum ada."""
    conn = sqlite3.connect("skincare.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skin_type TEXT NOT NULL,
            product_type TEXT NOT NULL,
            product_name TEXT NOT NULL,
            ingredients TEXT NOT NULL,
            suitability_reason TEXT NOT NULL
        )
    ''')
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        sample_data = [
            ("Berminyak", "Pembersih Wajah", "CeraVe Foaming Cleanser", "Asam Salisilat, Niacinamide", "Membersihkan minyak berlebih tanpa mengeringkan kulit, mengontrol kilap"),
            ("Berminyak", "Pelembap", "Neutrogena Hydro Boost Gel", "Asam Hialuronat, Gliserin", "Ringan, tidak menyumbat pori, melembapkan tanpa rasa berminyak"),
            ("Berminyak", "Tabir Surya", "La Roche-Posay Anthelios Clear Skin SPF 60", "Zinc Oxide, Silika", "Hasil matte, mengontrol minyak, perlindungan spektrum luas"),
            ("Kering", "Pembersih Wajah", "Cetaphil Gentle Skin Cleanser", "Gliserin, Niacinamide", "Melembapkan saat membersihkan, tidak mengiritasi kulit kering"),
            ("Kering", "Pelembap", "CeraVe Moisturizing Cream", "Seramida, Asam Hialuronat", "Memulihkan lapisan pelindung kulit, mengunci kelembapan"),
            ("Kering", "Tabir Surya", "EltaMD UV Clear SPF 46", "Zinc Oxide, Niacinamide", "Melembapkan, tidak berminyak, melindungi kulit kering sensitif"),
            ("Kombinasi", "Pembersih Wajah", "Innisfree Green Tea Foam Cleanser", "Ekstrak Teh Hijau, Asam Amino", "Menyeimbangkan minyak dan kelembapan untuk kulit kombinasi"),
            ("Kombinasi", "Pelembap", "Clinique Moisture Surge", "Lidah Buaya, Asam Hialuronat", "Ringan, melembapkan area kering tanpa menambah minyak"),
            ("Kombinasi", "Tabir Surya", "Biore UV Aqua Rich SPF 50", "Asam Hialuronat, Titanium Dioksida", "Ringan, tidak lengket, cocok untuk kulit kombinasi"),
            ("Berjerawat", "Pembersih Wajah", "PanOxyl Acne Foaming Wash", "Benzoyl Peroxide 10%", "Membunuh bakteri penyebab jerawat, mengurangi peradangan"),
            ("Berjerawat", "Pelembap", "Differin Oil-Free Moisturizer", "Gliserin, Allantoin", "Tidak menyumbat pori, menenangkan kulit setelah perawatan jerawat"),
            ("Berjerawat", "Tabir Surya", "Neutrogena Clear Face SPF 30", "Avobenzone, Oxybenzone", "Bebas minyak, tidak menyumbat pori, melindungi kulit berjerawat"),
            ("Sensitif", "Pembersih Wajah", "Vanicream Gentle Facial Cleanser", "Gliserin, Coco-Glucoside", "Bebas pewangi, lembut untuk kulit sensitif"),
            ("Sensitif", "Pelembap", "Avene Tolerance Extreme Cream", "Air Sumber Avene, Gliserin", "Menenangkan iritasi, hipoalergenik untuk kulit sensitif"),
            ("Sensitif", "Tabir Surya", "Blue Lizard Sensitive SPF 30", "Zinc Oxide, Titanium Dioksida", "Berbasis mineral, bebas pewangi, melindungi tanpa iritasi")
        ]
        c.executemany("INSERT INTO products (skin_type, product_type, product_name, ingredients, suitability_reason) VALUES (?, ?, ?, ?, ?)", sample_data)
    conn.commit()
    conn.close()

def query_db(skin_type):
    """Kueri produk perawatan kulit dari database SQLite berdasarkan tipe kulit."""
    conn = sqlite3.connect("skincare.db")
    c = conn.cursor()
    c.execute("SELECT product_type, product_name, ingredients, suitability_reason FROM products WHERE lower(skin_type) = lower(?)", (skin_type,))
    results = c.fetchall()
    conn.close()
    return results

def handle_api_key():
    """Menangani input untuk Google API Key."""
    if "api_key_set" not in st.session_state:
        st.session_state["api_key_set"] = False

    if st.session_state["api_key_set"]:
        return

    st.write("Masukkan Google API Key Anda untuk memulai:")

    with st.form(key="api_key_form"):
        api_key = st.text_input("API Key", type="password")
        submit_button = st.form_submit_button(label="Kirim")

        if submit_button and api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
            st.session_state["api_key_set"] = True
            st.rerun()

    if not st.session_state["api_key_set"]:
        st.stop()

def initialize_llm():
    """Inisialisasi LLM dengan prompt khusus untuk konsultasi perawatan kulit dalam bahasa Indonesia."""
    if "chain" not in st.session_state:
        system_prompt = """
        Anda adalah konsultan perawatan kulit profesional. Anda ahli dalam merekomendasikan produk untuk berbagai jenis kulit: berminyak, kering, kombinasi, berjerawat, dan sensitif.
        Selalu gunakan bahasa Indonesia untuk menjawab. Jika pengguna bertanya tentang rekomendasi untuk jenis kulit tertentu, periksa database terlebih dahulu. Jika tidak ada data, berikan rekomendasi umum berdasarkan pengetahuan Anda, termasuk jenis produk (misalnya, pembersih wajah, pelembap, tabir surya), bahan utama, dan alasan mengapa produk tersebut cocok.
        Untuk pertanyaan di luar perawatan kulit, arahkan kembali dengan sopan ke topik perawatan kulit.
        Jawaban harus singkat, informatif, dan dalam bahasa Indonesia. Jangan memberikan saran medis.
        """
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        st.session_state["chain"] = prompt_template | llm
    return st.session_state["chain"]

def manage_chat_history():
    """Kelola riwayat obrolan di session state."""
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = [
            AIMessage(content="Halo! Saya konsultan perawatan kulit Anda. Tanyakan tentang rekomendasi untuk kulit berminyak, kering, kombinasi, berjerawat, atau sensitif.")
        ]
    return st.session_state["chat_history"]

def show_message(message):
    """Tampilkan satu pesan obrolan."""
    role = "user" if isinstance(message, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(message.content)

def show_history(chat_history):
    """Tampilkan seluruh riwayat obrolan."""
    for msg in chat_history:
        show_message(msg)

def process_user_input(chain, chat_history):
    """Proses input pengguna, kueri database, dan dapatkan respons dari LLM jika diperlukan."""
    user_input = st.chat_input("Tanyakan tentang rekomendasi perawatan kulit...")
    if not user_input:
        return

    chat_history.append(HumanMessage(content=user_input))
    show_message(chat_history[-1])

    skin_types = ["berminyak", "kering", "kombinasi", "berjerawat", "sensitif"]
    matched_skin_type = None
    for skin_type in skin_types:
        if skin_type.lower() in user_input.lower():
            matched_skin_type = skin_type
            break

    if matched_skin_type:
        products = query_db(matched_skin_type)
        if products:
            response = f"Berikut adalah rekomendasi produk perawatan kulit untuk kulit **{matched_skin_type}**:\n\n"
            for product in products:
                product_type, product_name, ingredients, reason = product
                response += f"**{product_type}**: {product_name}\n- **Bahan Utama**: {ingredients}\n- **Mengapa Cocok**: {reason}\n\n"
            chat_history.append(AIMessage(content=response))
            show_message(chat_history[-1])
            return

    response = chain.invoke({"chat_history": chat_history[:-1], "input": user_input})
    chat_history.append(AIMessage(content=response.content))
    show_message(chat_history[-1])

def main_app():
    """Logika utama aplikasi."""
    init_db()
    handle_api_key()
    chain = initialize_llm()
    chat_history = manage_chat_history()
    show_history(chat_history)
    process_user_input(chain, chat_history)

main_app()