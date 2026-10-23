import sqlite3
import os
from datetime import datetime

class Database:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(base_dir, "quiz_system.db")
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Kích hoạt ràng buộc khóa ngoại (Foreign Keys)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Bảng Đề tài / Chủ đề
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 2. Bảng Câu hỏi trắc nghiệm
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    option_a TEXT NOT NULL,
                    option_b TEXT NOT NULL,
                    option_c TEXT NOT NULL,
                    option_d TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
                )
            ''')

            # 3. Bảng Kỳ thi Online
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS exams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    topic_id INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    status TEXT DEFAULT 'UPCOMING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (topic_id) REFERENCES topics(id)
                )
            ''')

            # 4. Bảng Kết quả thi của Thí sinh
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER NOT NULL,
                    student_name TEXT NOT NULL,
                    correct_count INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL,
                    score REAL NOT NULL,
                    completed_at TEXT NOT NULL,
                    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE
                )
            ''')
            conn.commit()

    # =========================================================================
    # QUẢN LÝ ĐỀ TÀI (TOPICS)
    # =========================================================================
    def add_topic(self, name, description=""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO topics (name, description) VALUES (?, ?)", (name, description))
            conn.commit()
            return cursor.lastrowid

    def get_topics(self):
        """Lấy danh sách đề tài kèm số lượng câu hỏi hiện có"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT t.id, t.name, t.description, COUNT(q.id) as question_count
                FROM topics t
                LEFT JOIN questions q ON t.id = q.topic_id
                GROUP BY t.id
                ORDER BY t.id DESC
            '''
            cursor.execute(query)
            return [dict(r) for r in cursor.fetchall()]

    # =========================================================================
    # QUẢN LÝ CÂU HỎI (QUESTIONS - CRUD)
    # =========================================================================
    def add_question(self, topic_id, question, a, b, c, d, correct):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO questions (topic_id, question, option_a, option_b, option_c, option_d, correct_answer)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (topic_id, question, a, b, c, d, correct.upper().strip()))
            conn.commit()

    def get_questions_by_topic(self, topic_id):
        """Lấy danh sách tất cả câu hỏi thuộc về một đề tài"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM questions WHERE topic_id = ?", (topic_id,))
            return [dict(r) for r in cursor.fetchall()]

    def update_question(self, question_id, question, a, b, c, d, correct):
        """Cập nhật nội dung câu hỏi và các đáp án"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE questions 
                SET question = ?, option_a = ?, option_b = ?, option_c = ?, option_d = ?, correct_answer = ?
                WHERE id = ?
            ''', (question, a, b, c, d, correct.upper().strip(), question_id))
            conn.commit()

    def delete_question(self, question_id):
        """Xóa một câu hỏi theo ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            conn.commit()

    # =========================================================================
    # QUẢN LÝ KỲ THI (EXAMS)
    # =========================================================================
    def add_exam(self, title, topic_id, start_time, duration):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO exams (title, topic_id, start_time, duration_minutes)
                VALUES (?, ?, ?, ?)
            ''', (title, topic_id, start_time, duration))
            conn.commit()

    def get_exams(self):
        """Lấy danh sách kỳ thi kèm tổng số thí sinh đã hoàn thành bài thi"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT e.id, e.title, t.name as topic_name, e.start_time, e.duration_minutes, e.status,
                       (SELECT COUNT(*) FROM results r WHERE r.exam_id = e.id) as participant_count
                FROM exams e
                JOIN topics t ON e.topic_id = t.id
                ORDER BY e.id DESC
            '''
            cursor.execute(query)
            return [dict(r) for r in cursor.fetchall()]

    def delete_exam(self, exam_id):
        """Xóa kỳ thi (các kết quả thi liên quan cũng tự động xóa nhờ ON DELETE CASCADE)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
            conn.commit()

    # =========================================================================
    # QUẢN LÝ KẾT QUẢ THI (RESULTS)
    # =========================================================================
    def save_exam_result(self, exam_id, student_name, correct_count, total_questions, score):
        """Lưu kết quả nộp bài của thí sinh kèm giờ hệ thống máy tính chuẩn"""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO results (exam_id, student_name, correct_count, total_questions, score, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (exam_id, student_name.strip(), correct_count, total_questions, score, now_str))
            conn.commit()

    def get_student_result_for_exam(self, exam_id, student_name):
        """Kiểm tra xem thí sinh đã thi kỳ thi này chưa để chặn không cho thi lại"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM results 
                WHERE exam_id = ? AND LOWER(TRIM(student_name)) = LOWER(TRIM(?))
                ORDER BY id DESC LIMIT 1
            ''', (exam_id, student_name))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_exam_results(self, exam_id):
        """Lấy danh sách tất cả thí sinh đã thi để Admin xem bảng điểm"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT student_name, correct_count, total_questions, score, completed_at
                FROM results
                WHERE exam_id = ?
                ORDER BY score DESC, completed_at ASC
            ''', (exam_id,))
            return [dict(r) for r in cursor.fetchall()]

    # =========================================================================
    # HÀM PHỤC VỤ PHÂN HỆ HỌC SINH (CLIENT)
    # =========================================================================
    def get_active_exams_for_student(self):
        """Lấy danh sách kỳ thi để hiển thị ở Sảnh chờ của thí sinh"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT e.id, e.title, e.topic_id, t.name as topic_name, 
                       e.start_time, e.duration_minutes, e.status,
                       COUNT(q.id) as question_count
                FROM exams e
                JOIN topics t ON e.topic_id = t.id
                LEFT JOIN questions q ON t.id = q.topic_id
                GROUP BY e.id
                ORDER BY e.start_time ASC
            '''
            cursor.execute(query)
            return [dict(r) for r in cursor.fetchall()]

    def get_exam_questions(self, topic_id):
        """Tải toàn bộ nội dung câu hỏi và 4 đáp án của đề tài cho thí sinh làm bài"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, question, option_a, option_b, option_c, option_d, correct_answer 
                FROM questions 
                WHERE topic_id = ?
            ''', (topic_id,))
            return [dict(r) for r in cursor.fetchall()]

if __name__ == "__main__":
    db = Database()
    print("[+] CSDL SQLite đã cập nhật thành công!")