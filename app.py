from flask import Flask, render_template, request, redirect, url_for, flash, session
from teacher_translator import LaoSiMiDaSystem
from Goldsent import GoldenSentenceGenerator
import os
import sqlite3

app = Flask(__name__)
app.secret_key = os.urandom(24)

# 確保用戶帳號資料表存在 (專門用來讓用戶創建帳號)
def init_user_auth_db():
    conn = sqlite3.connect('laosimida.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users_auth (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    # 順便建立一個預設的管理員帳號
    try:
        cursor.execute("INSERT INTO users_auth (username, password) VALUES (?, ?)", ("iamadmin", "admin123"))
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

# 🔑 登入功能
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash("請填寫帳號和密碼！", "danger")
            return render_template('login.html')
            
        conn = sqlite3.connect('laosimida.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users_auth WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] == password:
            session['current_user'] = username
            flash(f"歡迎回來，{username}！解密開始！", "success")
            return redirect(url_for('main_menu'))
        else:
            flash("帳號或密碼錯誤，請重新輸入，或先點擊下方創建帳號！", "danger")
            
    return render_template('login.html')

# 📝 創建帳號 (註冊) 功能
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash("帳號或密碼不能留空！", "danger")
            return render_template('register.html')
            
        conn = sqlite3.connect('laosimida.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users_auth (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash("帳號創建成功！請登入系統。", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("這個帳號已經被註冊過了，請換一個名字！", "danger")
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('current_user', None)
    return redirect(url_for('login'))

# 🏫 主功能頁面 (融合 5 大功能在一頁)
@app.route('/main_menu', methods=['GET', 'POST'])
def main_menu():
    if 'current_user' not in session:
        return redirect(url_for('login'))
    
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
        
        # 【功能 1 & 2】：翻譯解密
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
                    
                    # 🔥【功能 4 聯動】：自動發射抗 Emo 金句，修復之前的 Bug！
                    try:
                        random_gold = gold_logic.get_random_sentence()
                        if random_gold:
                            comfort_sentence = {
                                'content': random_gold['content'],
                                'author': random_gold['author']
                            }
                    except Exception as e:
                        print(f"金句生成錯誤: {e}")
                else:
                    flash(f"系統找不到關於「{text_input}」的密碼，快在下方投稿區新增吧！", "warning")
        
        # 🔥【功能 5】：投稿新創意（修正欄位名稱對齊 teacher_translator.py 的設計）
        elif form_action == 'add_idea':
            t_sentence = request.form.get('teacher_sentence', '').strip()
            trans_text = request.form.get('translation', '').strip()
            
            if t_sentence and trans_text:
                try:
                    msg = app_logic.add_idea(session['current_user'], t_sentence, trans_text)
                    flash(msg, "success")
                except Exception as e:
                    flash(f"投稿失敗 Error: {e}", "danger")
            else:
                flash("請完整填寫投稿內容！", "warning")

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
    """【功能 3】：認同度投票 """
    if 'current_user' not in session:
        return redirect(url_for('login'))
    app_logic = LaoSiMiDaSystem()
    app_logic.vote(int(sentence_id), is_agree == 'True')
    flash("評分成功！感謝你的反饋！", "success")
    return redirect(url_for('main_menu'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
