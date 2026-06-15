import streamlit as st
import sqlite3
import os
import random

# 🔥 強制設定 Streamlit 頁面標題與排版 (對齊你們報告的綠底黑板/清爽風調性)
st.set_page_config(page_title="「老」斯密碼翻譯系統 - 歐陽組", page_icon="🔑", layout="centered")

# ----------------- 資料庫初始化 -----------------
def get_db_connection():
    conn = sqlite3.connect('laosimida.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # 創建帳號密碼表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users_auth (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    # 確保原始 sentences 表存在 (對齊報告第18頁)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sentences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_sentence TEXT NOT NULL,
            translation TEXT NOT NULL,
            agree_count INTEGER DEFAULT 0,
            disagree_count INTEGER DEFAULT 0
        )
    """)
    # 確保用戶統計表存在
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_stats (
            username TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
    """)
    # 預設建立官方管理員帳號
    try:
        cursor.execute("INSERT INTO users_auth (username, password) VALUES (?, ?)", ("iamadmin", "admin123"))
        cursor.execute("INSERT INTO users_auth (username, password) VALUES (?, ?)", ("歐陽建泓隊", "admin123"))
    except sqlite3.IntegrityError:
        pass
    conn.commit()
    conn.close()

init_db()

# ----------------- Session 狀態管理 -----------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'current_user' not in st.session_state:
    st.session_state['current_user'] = None

# ----------------- 美化 CSS 注入 -----------------
# 根據報告規格：深綠色黑板框、原木滾邊
st.markdown("""
    <style>
    .main { background-color: #E6F3FF; }
    .blackboard {
        background-color: #1b3622;
        color: white;
        padding: 25px;
        border-radius: 12px;
        border-bottom: 8px solid #6d4c41;
        text-align: center;
        margin-bottom: 20px;
    }
    .gold-box {
        background: linear-gradient(135deg, #fffde7 0%, #fff9c4 100%);
        border-left: 6px solid #fbc02d;
        padding: 15px;
        border-radius: 8px;
        color: #7f6000;
        margin-top: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- 頁面邏輯 -----------------

# 🔓 情況 A：未登入 ➔ 顯示登入/註冊界面
if not st.session_state['logged_in']:
    st.markdown('<div class="blackboard"><h1>🔑 「老」斯密碼翻譯系統</h1><p>開發團隊：高二甲歐陽組</p></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔒 用戶登入", "📝 創建新帳號"])
    
    with tab1:
        st.subheader("歡迎回來，請登入")
        login_user = st.text_input("輸入 User ID (帳號):", key="login_u")
        login_pwd = st.text_input("輸入 Password (密碼):", type="password", key="login_p")
        if st.button("安全登入系统", type="primary"):
            conn = get_db_connection()
            user = conn.execute("SELECT * FROM users_auth WHERE username = ?", (login_user.strip(),)).fetchone()
            conn.close()
            if user and user['password'] == login_pwd.strip():
                st.session_state['logged_in'] = True
                st.session_state['current_user'] = login_user.strip()
                st.success(f"歡迎回來，{login_user.strip()}！正在載入解密系統...")
                st.rerun()
            else:
                st.error("帳號或密碼錯誤，請重新輸入！")
                
    with tab2:
        st.subheader("新用戶創建帳號")
        reg_user = st.text_input("設定您的新 User ID:", key="reg_u")
        reg_pwd = st.text_input("設定您的安全密碼:", type="password", key="reg_p")
        if st.button("確認創建並提交"):
            if not reg_user.strip() or not reg_pwd.strip():
                st.warning("帳號和密碼不能留空！")
            else:
                conn = get_db_connection()
                try:
                    conn.execute("INSERT INTO users_auth (username, password) VALUES (?, ?)", (reg_user.strip(), reg_pwd.strip()))
                    conn.commit()
                    st.success("帳號創建成功！請切換至「用戶登入」分頁進行登入。")
                except sqlite3.IntegrityError:
                    st.error("這個 User ID 已經被註冊過了，請換一個名字！")
                finally:
                    conn.close()

# 🎛️ 情況 B：已登入 ➔ 進入融合 5 大功能的主功能面板
else:
    user = st.session_state['current_user']
    
    # 頂部黑板 Banner
    st.markdown(f"""
        <div class="blackboard">
            <h2>🔑 「老」斯密碼翻譯系統</h2>
            <p>當前使用者：<b>{user}</b></p>
        </div>
    """, unsafe_allow_html=True)
    
    # 獲取計數器數據 (功能 1 頂部統計)
    conn = get_db_connection()
    # 個人累計
    cursor = conn.execute("SELECT count FROM user_stats WHERE username = ?", (user,))
    row = cursor.fetchone()
    p_count = row['count'] if row else 0
    # 全服累計
    row_total = conn.execute("SELECT SUM(count) as total FROM user_stats").fetchone()
    t_count = row_total['total'] if row_total['total'] else 0
    conn.close()
    
    # 數據看板展示
    col_a, col_b = st.columns(2)
    col_a.metric("📊 個人解密累計", f"{p_count} 次")
    col_b.metric("🌐 全服總解密量", f"{t_count} 次")
    
    st.markdown("---")
    
    # 核心排版：左右分欄
    col_left, col_right = st.columns([6, 4])
    
    with col_left:
        st.subheader("🔄 密碼雙向檢索解密")
        
        # 【功能 1 & 2】：模式切換
        mode = st.radio("選擇檢索模式：", ["🗣️ 功能 1：老師的話 ➔ 潛台詞", "💭 功能 2：潛台詞 ➔ 老師的話"], horizontal=True)
        
        # 搜尋輸入框
        search_label = "請輸入老師說的話 (例如：兩分鐘)：" if "功能 1" in mode else "請輸入你想反查的潛台詞："
        text_input = st.text_input(search_label, placeholder="輸入關鍵字進行模糊搜索...")
        
        if st.button("解密真實含意", type="primary"):
            if text_input.strip():
                conn = get_db_connection()
                # 模糊查詢
                if "功能 1" in mode:
                    res = conn.execute("SELECT * FROM sentences WHERE teacher_sentence LIKE ?", (f"%{text_input.strip()}%",)).fetchall()
                else:
                    res = conn.execute("SELECT * FROM sentences WHERE translation LIKE ?", (f"%{text_input.strip()}%",)).fetchall()
                
                if res:
                    # 更新個人統計
                    conn.execute("INSERT INTO user_stats (username, count) VALUES (?, 1) ON CONFLICT(username) DO UPDATE SET count=count+1", (user,))
                    conn.commit()
                    
                    matched = res[0]
                    st.success("🔍 破解成功！")
                    st.write(f"**查詢原文：** {matched['teacher_sentence']}")
                    st.subheader(f"🗣️ 解密含意： 「{matched['translation']}」")
                    
                    # 【功能 3】：認同度投票
                    st.markdown("**【功能 3】精準度評分：**")
                    c1, c2 = st.columns(2)
                    if c1.button(f"👍 這很精準 ({matched['agree_count']})", key=f"y_{matched['id']}"):
                        conn.execute("UPDATE sentences SET agree_count=agree_count+1 WHERE id=?", (matched['id'],))
                        conn.commit()
                        st.success("感謝評分！")
                        st.rerun()
                    if c2.button(f"👎 才不是這樣 ({matched['disagree_count']})", key=f"n_{matched['id']}"):
                        conn.execute("UPDATE sentences SET disagree_count=disagree_count+1 WHERE id=?", (matched['id'],))
                        conn.commit()
                        st.success("感謝反饋！")
                        st.rerun()
                else:
                    st.warning(f"系統庫找不到與「{text_input}」相關的密碼，快在下方投稿區新增吧！")
                conn.close()

    with col_right:
        st.subheader("✨ 功能 4：暖心發射器")
        st.caption("當在左側查詢出令高二學生沮喪的老師表面話後，系統會在此自動載入安慰金句。")
        
        # 這裡從現有的資料庫或備用列表中隨機抽一個正能量句子
        conn = get_db_connection()
        gold_sentences = conn.execute("SELECT * FROM sentences").fetchall()
        conn.close()
        
        # 如果資料庫是空的，我們提供一個預設的溫暖彩蛋列表避免報錯
        backup_jokes = [
            {"content": "考差了沒關係，進步空間很大！老師只是希望我們更好。", "author": "高二甲暖心學長"},
            {"content": "兩分鐘雖然很久，但剛好可以多學一個公式，穩賺不賠！", "author": "數學科代表"},
            {"content": "我們不是最差的一屆，我們是潛力最無窮的一屆！", "author": "歐陽組勵志金句"}
        ]
        
        joke = random.choice(backup_jokes)
        
        st.markdown(f"""
            <div class="gold-box">
                <h5>🌱 老斯密碼 · 暖心雞湯</h5>
                <p style='font-style: italic;'>「 {joke['content']} 」</p>
                <p style='text-align: right; margin-bottom: 0;'>—— 來自：<b>{joke['author']}</b></p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # 下方滿版：【功能 5】投稿新創意表單
    st.subheader("💡 功能 5：投稿新創意表單")
    st.caption("捕捉到學校老師的新名言了？在這裡提交上傳，數據將永久寫入 SQLite 資料庫！")
    
    with st.form("add_idea_form", clear_on_submit=True):
        t_sentence = st.text_input("老師說的話 (表面話) *", placeholder="例如：我就佔用大家兩分鐘")
        trans_text = st.text_input("真實潛台詞 (內心戲) *", placeholder="例如：這堂課我要拖到下堂課鐘響")
        submit_btn = st.form_submit_button("提交新創意審核")
        
        if submit_btn:
            if t_sentence.strip() and trans_text.strip():
                conn = get_db_connection()
                conn.execute("INSERT INTO sentences (teacher_sentence, translation) VALUES (?, ?)", (t_sentence.strip(), trans_text.strip()))
                conn.commit()
                conn.close()
                st.success("💡 投稿成功！新密碼已成功寫入 SQLite 資料庫！")
            else:
                st.warning("請完整填寫表面話和潛台詞！")

    # 安全登出
    if st.button("安全登出系統", color="red"):
        st.session_state['logged_in'] = False
        st.session_state['current_user'] = None
        st.rerun()
