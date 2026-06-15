import sqlite3
import datetime

class LaoSiMiDaSystem:
    def __init__(self, db_name='laosimida.db'):
        self.DBName = db_name
        self.setup_DB()

    def setup_DB(self):
        """初始化資料庫，建立四個核心資料表"""
        self.create_sentences_table()
        self.create_user_ideas_table()
        self.create_users_table()
        self.create_sentence_teachers_table() # 新增：建立語錄與老師關聯表
        self.init_default_data() # 初始化一些預設資料以免資料庫為空

    def get_connection(self):
        return sqlite3.connect(self.DBName)

    def create_sentences_table(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentences (
                sentence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_sentence TEXT NOT NULL,
                translation TEXT NOT NULL,
                agree_votes INTEGER DEFAULT 0,
                disagree_votes INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def create_user_ideas_table(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_ideas (
                idea_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                teacher_sentence TEXT NOT NULL,
                translation TEXT NOT NULL,
                is_official INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                submit_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def create_users_table(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                translate_count INTEGER DEFAULT 0,
                adopted_ideas INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
        
    def create_sentence_teachers_table(self):
        """新增：建立語錄對應的老師資料表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentence_teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_id INTEGER NOT NULL,
                teacher_name TEXT NOT NULL,
                votes INTEGER DEFAULT 0,
                FOREIGN KEY(sentence_id) REFERENCES sentences(sentence_id)
            )
        """)
        conn.commit()
        conn.close()

    def init_default_data(self):
        """插入一些預設的老師語錄"""
        default_data = [
            ('這道題我講過很多次了', '你們怎麼還是不會'),
            ('體育老師今天有事', '這節課改上數學'),
            ('整棟樓就你們班最吵', '其實每個班都被這麼說過'),
            ('再講兩分鐘就下課', '準備拖堂10分鐘'),
            ('看我幹嘛？看黑板！', '我臉上有答案嗎？'),
            ('看黑板幹嘛？看書！', '書上都有寫'),
            ('沒人舉手是吧？那我點名了', '死亡點名開始')
        ]
        conn = self.get_connection()
        cursor = conn.cursor()
        # 檢查是否已經有資料，沒有才插入
        cursor.execute("SELECT count(*) FROM sentences")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO sentences (teacher_sentence, translation) VALUES (?, ?)", default_data)
            conn.commit()
            print("初始化預設語錄完成！")
        conn.close()

    # --- 功能一：翻譯 (修改為關鍵詞搜尋) ---
    def search_sentences(self, input_text, mode='teacher_to_subtext'):
        """
        關鍵詞搜尋功能
        :param input_text: 輸入文字
        :param mode: 'teacher_to_subtext' (老師話->潛台詞) 或 'subtext_to_teacher' (潛台詞->老師話)
        :return: 返回所有符合的結果列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        sentence_data = None

        if mode == 'teacher_to_subtext':
            # 模糊搜尋老師的話，返回所有
            cursor.execute("SELECT * FROM sentences WHERE teacher_sentence LIKE ?", (f'%{input_text}%',))
            sentence_data = cursor.fetchall()
        else:
            # 模糊搜尋潛台詞，返回所有
            cursor.execute("SELECT * FROM sentences WHERE translation LIKE ?", (f'%{input_text}%',))
            sentence_data = cursor.fetchall()

        conn.close()
        return sentence_data # 返回的是一個列表

    def record_translation_event(self, user_id):
        """
        記錄使用者的翻譯次數 (在使用者確認翻譯結果後呼叫)
        """
        if user_id == 'guest':
            return

        conn = self.get_connection()
        cursor = conn.cursor()
        # 確保使用者存在
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        cursor.execute("UPDATE users SET translate_count = translate_count + 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

    # --- 功能二：使用者新增 Idea 與 管理員審核 ---
    def add_idea(self, user_id, teacher_sentence, translation):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_ideas (user_id, teacher_sentence, translation) 
            VALUES (?, ?, ?)
        """, (user_id, teacher_sentence, translation))
        
        # 確保使用者存在於 users 表
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        
        conn.commit()
        conn.close()
        return "提交成功！等待「歐陽建泓隊」審核。"

    def review_idea(self, admin_team, idea_id, action):
        """
        審核創意
        :param admin_team: 必須是 "歐陽建泓隊"
        :param action: 'approve' (通過) 或 'reject' (拒絕)
        """
        if admin_team != "歐陽建泓隊":
            return "權限不足：只有「歐陽建泓隊」可以修改資料庫！"

        conn = self.get_connection()
        cursor = conn.cursor()

        # 獲取 idea 資訊
        cursor.execute("SELECT * FROM user_ideas WHERE idea_id = ?", (idea_id,))
        idea = cursor.fetchone()
        
        if not idea:
            conn.close()
            return "找不到該 ID 的創意。"

        # idea 結構: 0:id, 1:user_id, 2:teacher_sentence, 3:translation, ...
        user_id = idea[1]
        t_sentence = idea[2]
        trans = idea[3]

        if action == 'approve':
            # 1. 更新 user_ideas 狀態
            cursor.execute("UPDATE user_ideas SET status='approved', is_official=1 WHERE idea_id=?", (idea_id,))
            # 2. 加入 sentences 表
            cursor.execute("INSERT INTO sentences (teacher_sentence, translation) VALUES (?, ?)", (t_sentence, trans))
            # 3. 增加使用者被採納數
            cursor.execute("UPDATE users SET adopted_ideas = adopted_ideas + 1 WHERE user_id=?", (user_id,))
            msg = f"已採納 ID {idea_id}，並更新至資料庫。"
        else:
            cursor.execute("UPDATE user_ideas SET status='rejected' WHERE idea_id=?", (idea_id,))
            msg = f"已駁回 ID {idea_id}。"

        conn.commit()
        conn.close()
        return msg

    def get_pending_ideas(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_ideas WHERE status = 'pending'")
        results = cursor.fetchall()
        conn.close()
        return results

    # --- 功能三：成就徽章 ---
    def check_badges(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT translate_count, adopted_ideas FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            return ["尚未有任何記錄"]

        t_count, a_count = result
        badges = []
        
        if t_count >= 10:
            badges.append("初露鋒芒 (翻譯滿10句)")
        if t_count >= 30:
            badges.append("熟能生巧 (翻譯滿30句)")
        if t_count >= 100:
            badges.append("潛台詞大師 (翻譯滿100句)")
        if a_count >= 5:
            badges.append("靈感迸發 (被採納5條創意)")
            
        if not badges:
            badges.append("目前無徽章，繼續加油！")
            
        return badges

    # --- 功能四：互動投票與優化列表 ---
    def vote(self, sentence_id, is_agree):
        conn = self.get_connection()
        cursor = conn.cursor()
        if is_agree:
            cursor.execute("UPDATE sentences SET agree_votes = agree_votes + 1 WHERE sentence_id = ?", (sentence_id,))
        else:
            cursor.execute("UPDATE sentences SET disagree_votes = disagree_votes + 1 WHERE sentence_id = ?", (sentence_id,))
        conn.commit()
        conn.close()
        return "投票成功！感謝您的反饋。"

    def get_low_agreement_sentences(self):
        """
        獲取低認同度的句子供團隊審核優化
        定義：總票數 > 5 且 認同率 < 50%
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        # 查詢並計算認同率 (agree / (agree + disagree))
        cursor.execute("""
            SELECT sentence_id, teacher_sentence, translation, agree_votes, disagree_votes 
            FROM sentences 
            WHERE (agree_votes + disagree_votes) > 5 
            AND (CAST(agree_votes AS FLOAT) / (agree_votes + disagree_votes)) < 0.5
        """)
        results = cursor.fetchall()
        conn.close()
        return results

    # --- 新增功能：獲取翻譯次數 ---
    def get_user_translation_count(self, user_id):
        """獲取單一使用者的翻譯次數"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT translate_count FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def get_total_translation_count(self):
        """獲取所有使用者的總翻譯次數"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(translate_count) FROM users")
        result = cursor.fetchone()
        conn.close()
        # 確保 result[0] 不是 None
        return result[0] if result and result[0] is not None else 0

    # --- 新增功能：老師關聯 ---
    def add_teacher_association(self, sentence_id, teacher_name):
        """將一位老師與某句語錄關聯"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # 檢查是否已經重複
        cursor.execute("SELECT id FROM sentence_teachers WHERE sentence_id = ? AND teacher_name = ?", (sentence_id, teacher_name))
        if cursor.fetchone():
            conn.close()
            return "這位老師已經在名單中了！"
        
        cursor.execute("INSERT INTO sentence_teachers (sentence_id, teacher_name) VALUES (?, ?)", (sentence_id, teacher_name))
        conn.commit()
        conn.close()
        return "新增成功！"

    def get_associated_teachers(self, sentence_id):
        """獲取常說這句話的老師列表，按票數排序"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, teacher_name, votes FROM sentence_teachers WHERE sentence_id = ? ORDER BY votes DESC", (sentence_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def vote_associated_teacher(self, association_id):
        """為某個關聯老師投票"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE sentence_teachers SET votes = votes + 1 WHERE id = ?", (association_id,))
        conn.commit()
        conn.close()
        return "投票成功！"