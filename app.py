from flask import Flask, render_template, request, redirect, url_for, flash, session
from teacher_translator import LaoSiMiDaSystem
from Goldsent import GoldenSentenceGenerator  # 完美導入你的金句系統
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用於 session 加密
app.config['SESSION_TYPE'] = 'filesystem'

# 初始化後端系統（這兩個系統在啟動時都會自動建立對應的 .db 檔案）
app_logic = LaoSiMiDaSystem()
gold_logic = GoldenSentenceGenerator()

# 全域變數
bg_color = "#E6F3FF"

@app.route('/')
def index():
    """首頁，導向登入頁"""
    if 'current_user' in session:
        return redirect(url_for('main_menu'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登入頁面"""
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
    """登出"""
    session.pop('current_user', None)
    flash("已成功登出", "info")
    return redirect(url_for('login'))

@app.route('/main_menu')
def main_menu():
    """主選單"""
    if 'current_user' not in session:
        return redirect(url_for('login'))
    
    try:
        p_count = app_logic.get_user_translation_count(session['current_user'])
        t_count = app_logic.get_total_translation_count()
    except Exception as e:
        p_count = 0
        t_count = 0
    
    is_admin = session['current_user'] == 'iamadmin'
    
    return render_template(
        'main_menu.html',
        current_user=session['current_user'],
        personal_count=p_count,
        total_count=t_count,
        is_admin=is_admin,
        bg_color=bg_color
    )

@app.route('/translate/<mode>', methods=['GET', 'POST'])
def translate(mode):
    """翻譯頁面（依照片要求：移除關聯老師，整合自動金句生成功能）"""
    if 'current_user' not in session:
        return redirect(url_for('login'))
    
    result = None
    admin_stats = None
    comfort_sentence = None  # 用於存放要送給學生的安慰金句
    sentence_id = None
    text_input = ""
    
    if request.method == 'POST':
        text_input = request.form.get('text_input', '').strip()
        
        if text_input:
            # 執行翻譯搜尋
            res = app_logic.search_sentences(text_input, mode=mode)
            
            if res:
                confirmed_sentence_data = res[0]
                
                if confirmed_sentence_data:
                    app_logic.record_translation_event(session['current_user'])
                    s_id = confirmed_sentence_data[0]
                    agree_v = confirmed_sentence_data[3]
                    disagree_v = confirmed_sentence_data[4]
                    
                    if mode == 'teacher_to_subtext':
                        original_text = confirmed_sentence_data[1]
                        translated_text = confirmed_sentence_data[2]
                    else:
                        original_text = confirmed_sentence_data[2]
                        translated_text = confirmed_sentence_data[1]
                    
                    result = {
                        'original': original_text,
                        'translated': translated_text
                    }
                    
                    if session['current_user'] == 'iamadmin':
                        admin_stats = {'agree': agree_v, 'disagree': disagree_v}
                    
                    sentence_id = s_id
                    
                    # ✨【核心結合：自動生成安慰金句】✨
                    # 當查完老師的話，立刻從你的 Goldsent 隨機抓取一句溫暖的句子塞入前端網頁
                    try:
                        random_gold = gold_logic.get_random_sentence()
                        if random_gold:
                            comfort_sentence = {
                                'content': random_gold['content'],
                                'author': random_gold['author']
                            }
                    except Exception as e:
                        print(f"獲取金句失敗: {e}")
            else:
                flash(f"找不到關於「{text_input}」的翻譯，請考慮投稿", "warning")
                pre_teacher = text_input if mode == 'teacher_to_subtext' else ""
                pre_subtext = text_input if mode == 'subtext_to_teacher' else ""
                return redirect(url_for('add_idea', pre_teacher=pre_teacher, pre_subtext=pre_subtext))
    
    title_text = "老師的話 ➔ 潛台詞" if mode == 'teacher_to_subtext' else "潛台詞 ➔ 老師的話"
    input_label = "請輸入老師說的話:" if mode == 'teacher_to_subtext' else "請輸入潛台詞:"
    
    return render_template(
        'translate.html',
        bg_color=bg_color,
        title_text=title_text,
        input_label=input_label,
        mode=mode,
        text_input=text_input,
        result=result,
        admin_stats=admin_stats,
        comfort_sentence=comfort_sentence,  # 傳遞到你的網頁中顯示
        sentence_id=sentence_id,
        current_user=session['current_user']
    )

@app.route('/vote/<sentence_id>/<is_agree>')
def vote(sentence_id, is_agree):
    """認同/不認同投票功能"""
    if 'current_user' not in session: return redirect(url_for('login'))
    app_logic.vote(int(sentence_id), is_agree == 'True')
    flash("感謝您的反饋！您的意見將讓系統更準確。", "success")
    return redirect(request.referrer or url_for('main_menu'))

@app.route('/add_idea', methods=['GET', 'POST'])
def add_idea():
    if 'current_user' not in session: return redirect(url_for('login'))
    pre_teacher = request.args.get('pre_teacher', '')
    pre_subtext = request.args.get('pre_subtext', '')
    if request.method == 'POST':
        teacher_text = request.form.get('teacher_text', '').strip()
        subtext = request.form.get('subtext', '').strip()
        if teacher_text and subtext:
            msg = app_logic.add_idea(session['current_user'], teacher_text, subtext)
            flash(msg, "success")
            return redirect(url_for('main_menu'))
        else:
            flash("請完整填寫老師的話與潛台詞！", "warning")
    return render_template('add_idea.html', bg_color=bg_color, pre_teacher=pre_teacher, pre_subtext=pre_subtext, current_user=session['current_user'])

@app.route('/badges')
def badges():
    if 'current_user' not in session: return redirect(url_for('login'))
    badges = app_logic.check_badges(session['current_user'])
    return render_template('badges.html', bg_color=bg_color, current_user=session['current_user'], badges=badges)

@app.route('/low_agreement')
def low_agreement():
    if 'current_user' not in session: return redirect(url_for('login'))
    rows = app_logic.get_low_agreement_sentences()
    return render_template('low_agreement.html', bg_color=bg_color, current_user=session['current_user'], rows=rows)

@app.route('/admin_panel')
def admin_panel():
    if 'current_user' not in session or session['current_user'] != 'iamadmin':
        flash("權限不足！此區域僅限管理員進入。", "danger")
        return redirect(url_for('main_menu'))
    pendings = app_logic.get_pending_ideas()
    return render_template('admin_panel.html', bg_color="#FDF2E9", current_user=session['current_user'], pendings=pendings)

@app.route('/review_idea/<idea_id>/<action>')
def review_idea(idea_id, action):
    if 'current_user' not in session or session['current_user'] != 'iamadmin':
        flash("權限不足！", "danger")
        return redirect(url_for('main_menu'))
    result_msg = app_logic.review_idea("歐陽建泓隊", int(idea_id), action)
    flash(result_msg,
