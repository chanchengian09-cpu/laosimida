import sqlite3
import random

class GoldenSentenceGenerator:
    def __init__(self, db_name="sentences.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        # 修正：必須先建立資料表，否則新資料庫會報錯
        self._create_table()

    def _create_table(self):
        """初始化資料表結構"""
        sql = '''CREATE TABLE IF NOT EXISTS golden_table (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    category TEXT,
                    author TEXT,
                    source TEXT)'''
        self.cursor.execute(sql)
        self.conn.commit()

    def _to_dict(self, row):
        if row:
            return dict(row)
        return None

    # --- 新增：主程式需要的基礎操作 (CRUD) ---

    def add_sentence(self, content, category, author, source):
        """新增金句至資料庫"""
        sql = "INSERT INTO golden_table (content, category, author, source) VALUES (?, ?, ?, ?)"
        self.cursor.execute(sql, (content, category, author, source))
        self.conn.commit()

    def get_sentence_by_id(self, sid):
        """根據 ID 讀取單筆資料（修改功能的核心）"""
        self.cursor.execute("SELECT * FROM golden_table WHERE id = ?", (sid,))
        return self._to_dict(self.cursor.fetchone())

    def update_sentence(self, sid, content, category, author, source):
        """更新已存在的金句"""
        sql = "UPDATE golden_table SET content=?, category=?, author=?, source=? WHERE id=?"
        self.cursor.execute(sql, (content, category, author, source, sid))
        self.conn.commit()

    def delete_sentence(self, sid):
        """刪除特定 ID 的金句"""
        self.cursor.execute("DELETE FROM golden_table WHERE id = ?", (sid,))
        self.conn.commit()

    # --- 原有的檢索功能 ---

    def get_authors(self):
        self.cursor.execute("SELECT DISTINCT author FROM golden_table")
        return [row['author'] for row in self.cursor.fetchall() if row['author']]

    def get_categories(self):
        self.cursor.execute("SELECT DISTINCT category FROM golden_table")
        return [row['category'] for row in self.cursor.fetchall() if row['category']]

    def get_sources(self):
        self.cursor.execute("SELECT DISTINCT source FROM golden_table")
        return [row['source'] for row in self.cursor.fetchall() if row['source']]

    # --- 產生金句功能 ---

    def get_sentences_by_author(self, author):
        self.cursor.execute("SELECT * FROM golden_table WHERE author = ?", (author,))
        return [self._to_dict(row) for row in self.cursor.fetchall()]

    def get_sentences_by_category(self, category):
        self.cursor.execute("SELECT * FROM golden_table WHERE category = ?", (category,))
        return [self._to_dict(row) for row in self.cursor.fetchall()]

    def get_sentences_by_source(self, source):
        self.cursor.execute("SELECT * FROM golden_table WHERE source = ?", (source,))
        return [self._to_dict(row) for row in self.cursor.fetchall()]

    def get_random_sentence(self):
        self.cursor.execute("SELECT * FROM golden_table ORDER BY RANDOM() LIMIT 1")
        return self._to_dict(self.cursor.fetchone())

    def close(self):
        self.conn.close()