from flask import Flask, render_template, request, redirect, url_for, flash, session
from teacher_translator import LaoSiMiDaSystem
from Goldsent import GoldenSentenceGenerator
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'

# 全域變數顏色（配合你們報告的柔和風格）
bg_color = "#E6F3FF"

@app.route('/')
def index():
    if 'current_user' in session:
        return redirect(url_for('main_menu'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        if not user_id:
            user_id = "Student_A"
        session['current_user'] = user_id
        flash(f"歡迎回來，{user_id}！", "success")
        return redirect(url_for('main_menu'))
    return render_template('login.html', bg_color=bg_color)

@app.route('/logout')
def logout():
    session.pop('current_user', None)
    return redirect(url_for('login'))

@app.route('/main_menu', methods=['GET', 'POST'])
def main_menu():
    """全功能一頁式主頁面：將翻譯、金句、投稿、投票、數據統計完整融合"""
    if 'current_user' not in session:
        return redirect(url_for('login'))
    
    # 每次請求時才初始化，避免 SQLite 執行緒衝突報錯 (Error 核心修正)
    app_logic = LaoSiMiDaSystem()
    gold_logic = GoldenSentenceGenerator()
    
    result = None
    comfort_sentence = None
    sentence_id = None
    text_input = ""
    mode = request.args.get('mode', 'teacher_to_subtext') # 預設老師轉潛台詞
    
    # 獲取報告要求的頂部狀態數據
    try:
        p_count = app_logic.get_user_translation_count(session['current_user'])
        t_count = app_logic.get_total_translation_count()
    except:
        p_count, t_count = 0, 0

    # 處理表單提交
    if request.method == 'POST':
        action = request.form.get('action')
        
        # 功能 1 & 2：雙向解密翻譯
        if action == 'translate':
            text_input = request.form.get('text_input', '').strip()
            if text_input:
                res = app_logic.search_sentences(text_input, mode=mode)
                if res:
                    app_logic.record_translation_event(session['current_user'])
                    confirmed_data = res[0]
                    sentence_id = confirmed_data[0]
                    
                    # 依模式撈取正確文字
                    if mode == 'teacher_to_subtext':
                        orig, trans = confirmed_data[1], confirmed_data[2]
                    else:
                        orig, trans = confirmed_data[2], confirmed_data[1]
                        
                    result = {'original': orig, 'translated': trans}
                    
                    # 功能 4：聯動觸發金句生成器 (自動送出安慰)
                    try:
                        random_gold = gold_logic.get_random_sentence()
                        if random_gold:
                            comfort_sentence = {
                                'content': random_gold['content'],
                                'author': random_gold['author']
                            }
                    except Exception as e:
                        print(f"金句生成失敗: {e}")
                else:
                    flash(f"找不到關於「{text_input}」的密碼，快在下方投稿新創意吧！", "warning")
                    
        # 功能 5：投稿新創意 (修正原本欄位不對稱造成的 Error)
        elif action == 'add_idea':
            t_text = request.form.get('teacher_text', '').strip()
            s_text = request.form.get('subtext', '').strip()
            if t_text and s_text:
                try:
                    # 調用你們原有報告的 add_idea 機制
                    msg = app_logic.add_idea(session['current_user'], t_text, s_text)
                    flash(msg, "success")
                except Exception as e:
                    flash(f"投稿失敗: {e}", "danger")
            else:
                flash(f"請填寫完整內容再送出！", "warning")

    return render_template(
        'main_menu.html',
        current_user=session['current_user'],
        personal_count=p_count,
        total_count=t_count,
        result=result,
        comfort_sentence=comfort_sentence,
        sentence_id=sentence_id,
        text_input=text_input,
        mode=mode,
        bg_color=bg_color
    )

@app.route('/vote/<sentence_id>/<is_agree>')
def vote(sentence_id, is_agree):
    """功能 3：認同度投票"""
    if 'current_user' not in session: 
        return redirect(url_for('login'))
    app_logic = LaoSiMiDaSystem()
    app_logic.vote(int(sentence_id), is_agree == 'True')
    flash("投票成功！感謝你的反饋！", "success")
    return redirect(url_for('main_menu'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
