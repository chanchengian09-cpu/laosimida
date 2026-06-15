import streamlit as st
import random
from teacher_translator import LaoSiMiDaSystem
from Goldsent import GoldenSentenceGenerator

# 1. Page Configuration (Sets title and app name)
st.set_page_config(page_title="老斯密碼 LaoSiMiDa", page_icon="🔑", layout="centered")

# 2. Initialize your existing logic systems
@st.cache_resource
def init_systems():
    translator = LaoSiMiDaSystem()
    golden_gen = GoldenSentenceGenerator()
    
    # Pre-populate the 10-minute extension warm sentences if empty
    if not golden_gen.get_sentences_by_category("延長下課"):
        golden_gen.add_sentence(
            content="各位同學，老師再佔用大家10分鐘。別擔心，下課後外面有溫暖的陽光，擦擦眼前的汗水，我們把這精彩的尾聲聽完，等會點心吃起來更甜！",
            category="延長下課",
            author="暖心班導",
            source="老斯密碼"
        )
        golden_gen.add_sentence(
            content="我知道大家都累了，這最後的10分鐘是我們一起堅持的勳章。堅持住，等一下下課老師帶頭衝福利社！",
            category="延長下課",
            author="熱血體育老師",
            source="老斯密碼"
        )
    return translator, golden_gen

app_logic, golden_logic = init_systems()

# 3. Application Header
st.title("🔑 老斯密碼 (LaoSiMiDa)")
st.caption("為學生打造的老師潛台詞翻譯器 & 暖心金句發射器")

# 4. User Login Setup (Simple Streamlit Sidebar)
st.sidebar.header("👤 使用者設定")
user_id = st.sidebar.text_input("輸入你的學號/暱稱", value="Student_A").strip()
st.sidebar.write(f"歡迎回來，**{user_id}**！")

# Display Stats in Sidebar
try:
    p_count = app_logic.get_user_translation_count(user_id)
    t_count = app_logic.get_total_translation_count()
    st.sidebar.metric("你的翻譯次數", p_count)
    st.sidebar.metric("全服總翻譯量", t_count)
except:
    pass

# 5. App Navigation (Tabs make it incredibly easy to switch features)
tab1, tab2, tab3 = st.tabs(["🗣️ 密碼翻譯器", "✨ 金句模擬器", "💡 投稿新密碼"])

# --- TAB 1: TRANSLATOR ---
with tab1:
    st.header("老師話術密碼解密")
    mode = st.radio("選擇翻譯模式:", ["老師的話 ➔ 潛台詞", "潛台詞 ➔ 老師的話"])
    
    search_mode = 'teacher_to_subtext' if mode == "老師的話 ➔ 潛台詞" else 'subtext_to_teacher'
    text_input = st.text_input("請輸入關鍵字搜尋 (例如: 兩分鐘、下課):", placeholder="在這裡輸入...")
    
    if st.button("解密翻譯", type="primary"):
        if text_input:
            res = app_logic.search_sentences(text_input, mode=search_mode)
            if res:
                confirmed_data = res[0]
                s_id = confirmed_data[0]
                
                # Identify original and translated text based on mode
                orig, trans = (confirmed_data[1], confirmed_data[2]) if search_mode == 'teacher_to_subtext' else (confirmed_data[2], confirmed_data[1])
                
                # Record event
                app_logic.record_translation_event(user_id)
                
                # Display Results beautifully using built-in info/warning blocks
                st.info(f"**原文：** {orig}")
                st.warning(f"**💡 老斯真實潛台詞：** \n\n ### 「 {trans} 」")
                
                # Voting Section inside expanding box
                with st.expander("📊 這句精準嗎？幫忙評個分"):
                    col1, col2 = st.columns(2)
                    if col1.button("👍 這很精準", key=f"agree_{s_id}"):
                        app_logic.vote(s_id, True)
                        st.success("感謝認同！")
                    if col2.button("👎 瞎扯，才不是這樣", key=f"diagree_{s_id}"):
                        app_logic.vote(s_id, False)
                        st.error("收到反饋！")
                
                # Teacher association list
                st.subheader("👨‍🏫 誰最常說這句話？")
                teachers = app_logic.get_associated_teachers(s_id)
                for t in teachers:
                    st.write(f"- **{t[1]}** 老師 ({t[2]}票)")
                    
                # Nominate a teacher
                new_teacher = st.text_input("提名我們學校常說這句話的老師:", key=f"t_input_{s_id}")
                if st.button("送出提名", key=f"t_btn_{s_id}"):
                    if new_teacher:
                        msg = app_logic.add_teacher_association(s_id, new_teacher)
                        st.success(msg)
            else:
                st.error(f"找不到關於「{text_input}」的翻譯。請到『投稿新密碼』分頁提供靈感！")

# --- TAB 2: GOLD SENTENCE SIMULATOR ---
with tab2:
    st.header("✨ 老斯密碼金句模擬器")
    st.write("今天課堂上又痛苦了嗎？來一劑老斯的心靈雞湯！")
    
    # The feature you requested: Special button for class extensions!
    if st.button("🚨 救命！老師又要延遲下課 10 分鐘了！", type="secondary", use_container_width=True):
        sentences = golden_logic.get_sentences_by_category("延長下課")
        if sentences:
            picked = random.choice(sentences)
            st.success(f"### 「 {picked['content']} 」 \n\n —— *來自：{picked['author']}*")
            
    if st.button("🎲 隨機來一句普通老斯金句", use_container_width=True):
        picked = golden_logic.get_random_sentence()
        if picked:
            st.success(f"### 「 {picked['content']} 」 \n\n —— *來自：{picked['author']} (分類: {picked['category']})*")

# --- TAB 3: SUBMIT NEW IDEA ---
with tab3:
    st.header("💡 投稿新靈感")
    t_text = st.text_input("老師說的話:")
    s_text = st.text_input("真正的潛台詞:")
    if st.button("提交審查"):
        if t_text and s_text:
            msg = app_logic.add_idea(user_id, t_text, s_text)
            st.success(msg)
        else:
            st.error("請完整填寫欄位！")