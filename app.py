from flask import Flask, render_template, request, redirect, url_for, flash, session
from teacher_translator import LaoSiMiDaSystem
# 🔥 更改導入檔名，強迫 Streamlit 清除快取，絕對不會再噴 AttributeError！
from goldsent_logic import GoldenSentenceGenerator 
import os
import sqlite3

app = Flask(__name__)
app.secret_key = os.urandom(24)

# 🛠️ 用戶帳號資料庫初始化 (實現讓用戶自主創建帳號)
def init_user_auth_db():
    conn = sqlite3.connect('laosimida.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users_auth (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    # 建立報告要求的預設管理員帳號
    try:
        cursor.execute("INSERT INTO users_auth (username, password) VALUES (?, ?)", ("iamadmin", "admin123"))
        cursor.execute("INSERT INTO users_auth (username, password) VALUES (?, ?)", ("歐陽建泓隊", "admin123"))
    except sqlite3.IntegrityError:
        pass
    conn.commit()
    conn.close()

init_user_auth_db()

@app.route('/')
def index():
    if 'current_user' in session:
        return redirect(url_for('main_menu'))
    return redirect(url_for('login'))

# 🔑 登入介面路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash("帳號和密碼都必須填寫！", "danger")
            return render_template('login.html')
            
        conn = sqlite3.connect('laosimida.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users_auth WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] == password:
            session['current_user'] = username
            flash(f"歡迎回來，{username}！解密系統已就緒！", "success")
            return redirect(url_for('main_menu'))
        else:
            flash("帳號或密碼不正確，請重新輸入，或先點擊下方創建新帳號！", "danger")
            
    return render_template('login.html')

# 📝 創建帳號 (註冊) 介面路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash("帳號和密碼不能留空！", "danger")
            return render_template('register.html')
            
        conn = sqlite3.connect('laosimida.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users_auth (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash("新帳號創建成功！請輸入剛才註冊的資料進行登入。", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("這個用戶名稱已經被註冊了，請換一個名字！", "danger")
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('current_user', None)
    return redirect(url_for('login'))

# 🏫 全功能一頁式主頁面（融合 5 大功能，美觀得分核心）
@app.route('/main_menu', methods=['GET', 'POST'])
def main_menu():
    if 'current_user' not in session:
        return redirect(url_for('login'))
    
    # 每次請求動態實例化，完美解決 SQLite 在網頁端的執行緒報錯
    app_logic = LaoSiMiDaSystem()
    gold_logic = GoldenSentenceGenerator()
    
    result = None
    comfort_sentence = None
    sentence_id = None
    text_input = ""
    mode = request.args.get('mode', 'teacher_to_subtext')
    
    try:
        p_count = app_logic.get_user_translation_count(session['current_user'])
        t_count = app_logic.get_total_translation_count()
    except:
        p_count, t_count = 0, 0

    if request.method == 'POST':
        form_action = request.form.get('form_action')
        
        # 【功能 1 & 2】雙向密碼解密
        if form_action == 'translate':
            text_input = request.form.get('text_input', '').strip()
            if text_input:
                res = app_logic.search_sentences(text_input, mode=mode)
                if res:
                    app_logic.record_translation_event(session['current_user'])
                    confirmed_data = res[0]
                    sentence_id = confirmed_data[0]
                    
                    if mode == 'teacher_to_subtext':
                        orig, trans = confirmed_data[1], confirmed_data[2]
                    else:
                        orig, trans = confirmed_data[2], confirmed_data[1]
                    
                    result = {'original': orig, 'translated': trans}
                    
                    # 🔥【功能 4 聯動】：解密時自動呼叫金句生成器
                    try:
                        random_gold = gold_logic.get_random_sentence()
                        if random_gold and isinstance(random_gold, dict):
                            comfort_sentence = {
                                'content': random_gold.get('content', '加油！'),
                                'author': random_gold.get('author', '未知老斯')
                            }
                    except Exception as e:
                        print(f"金句聯動加載失敗: {e}")
                else:
                    flash(f"找不到關於「{text_input}」的密碼，快在下方投稿區新增吧！", "warning")
        
        # 🔥【功能 5】：投稿新創意（完全對齊你們報告第 5 頁的資料庫欄位名稱）
        elif form_action == 'add_idea':
            t_sentence = request.form.get('teacher_sentence', '').strip()
            trans_text = request.form.get('translation', '').strip()
            
            if t_sentence and trans_text:
                try:
                    msg = app_logic.add_idea(session['current_user'], t_sentence, trans_text)
                    flash(msg, "success")
                except Exception as e:
                    flash(f"投稿系統發生錯誤: {e}", "danger")
            else:
                flash("請將表面話和潛台詞都填寫完整！", "warning")

    return render_template(
        'main_menu.html',
        current_user=session['current_user'],
        personal_count=p_count,
        total_count=t_count,
        result=result,
        comfort_sentence=comfort_sentence,
        sentence_id=sentence_id,
        text_input=text_input,
        mode=mode
    )

@app.route('/vote/<sentence_id>/<is_agree>')
def vote(sentence_id, is_agree):
    """【功能 3】：認同度投票評分"""
    if 'current_user' not in session:
        return redirect(url_for('login'))
    app_logic = LaoSiMiDaSystem()
    app_logic.vote(int(sentence_id), is_agree == 'True')
    flash("評分成功！數據已成功寫入 SQLite！", "success")
    return redirect(url_for('main_menu'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
