import sqlite3
import os
from datetime import datetime
import hashlib

DB_PATH = os.path.join(os.path.dirname(__file__), 'quiz_system.db')

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Bảng tài khoản người dùng / thí sinh
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')

            # 2. Bảng chủ đề / đề tài
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT
                )
            ''')

            # 3. Bảng câu hỏi (hỗ trợ đoạn văn đọc hiểu)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER NOT NULL,
                    passage TEXT,
                    question TEXT NOT NULL,
                    option_a TEXT NOT NULL,
                    option_b TEXT NOT NULL,
                    option_c TEXT NOT NULL,
                    option_d TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
                )
            ''')

            # 4. Bảng ca thi / kỳ thi trực tuyến
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS exams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
                )
            ''')

            # 5. Bảng kết quả bài làm của thí sinh (Đã có cột violations)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER NOT NULL,
                    student_name TEXT NOT NULL,
                    correct_count INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL,
                    score REAL NOT NULL,
                    violations INTEGER DEFAULT 0,
                    completed_at TEXT NOT NULL,
                    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE
                )
            ''')

            # Tự động cập nhật cột violations nếu CSDL cũ chưa có
            try:
                cursor.execute("ALTER TABLE results ADD COLUMN violations INTEGER DEFAULT 0")
            except Exception:
                pass

            conn.commit()

    # =========================================================================
    # QUẢN LÝ TÀI KHOẢN (AUTH)
    # =========================================================================
    def register_user(self, username, password, full_name):
        """Đăng ký tài khoản mới cho thí sinh"""
        pwd_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password_hash, full_name, created_at) VALUES (?, ?, ?, ?)",
                    (username.strip(), pwd_hash, full_name.strip(), now_str)
                )
                conn.commit()
                return True, "Đăng ký tài khoản thành công!"
        except sqlite3.IntegrityError:
            return False, "Tên đăng nhập đã tồn tại, vui lòng chọn tên khác!"
        except Exception as e:
            return False, f"Lỗi hệ thống: {e}"

    def authenticate_user(self, username, password):
        """Xác thực đăng nhập thí sinh"""
        pwd_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username, full_name FROM users WHERE username = ? AND password_hash = ?",
                (username.strip(), pwd_hash)
            )
            row = cursor.fetchone()
            if row:
                return True, dict(row)
            return False, None

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
            return [dict(row) for row in cursor.fetchall()]

    def delete_topic(self, topic_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
            conn.commit()

    # =========================================================================
    # QUẢN LÝ CÂU HỎI (QUESTIONS)
    # =========================================================================
    def add_question(self, topic_id, question, option_a, option_b, option_c, option_d, correct_answer):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO questions (topic_id, question, option_a, option_b, option_c, option_d, correct_answer)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (topic_id, question, option_a, option_b, option_c, option_d, correct_answer))
            conn.commit()
            return cursor.lastrowid

    def add_passage_questions(self, topic_id, passage, questions_list):
        """Thêm cụm câu hỏi thuộc một bài đọc hiểu"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for q_data in questions_list:
                cursor.execute('''
                    INSERT INTO questions (topic_id, passage, question, option_a, option_b, option_c, option_d, correct_answer)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    topic_id,
                    passage.strip(),
                    q_data["question"].strip(),
                    q_data["a"].strip(),
                    q_data["b"].strip(),
                    q_data["c"].strip(),
                    q_data["d"].strip(),
                    q_data["correct"].strip().upper()
                ))
            conn.commit()

    def get_questions_by_topic(self, topic_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM questions WHERE topic_id = ? ORDER BY id ASC", (topic_id,))
            return [dict(row) for row in cursor.fetchall()]

    def update_question(self, question_id, question, option_a, option_b, option_c, option_d, correct_answer):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE questions
                SET question = ?, option_a = ?, option_b = ?, option_c = ?, option_d = ?, correct_answer = ?
                WHERE id = ?
            ''', (question, option_a, option_b, option_c, option_d, correct_answer, question_id))
            conn.commit()

    def delete_question(self, question_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            conn.commit()

    # =========================================================================
    # QUẢN LÝ KỲ THI (EXAMS)
    # =========================================================================
    def add_exam(self, topic_id, title, duration_minutes, start_time):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO exams (topic_id, title, duration_minutes, start_time)
                VALUES (?, ?, ?, ?)
            ''', (topic_id, title, duration_minutes, start_time))
            conn.commit()
            return cursor.lastrowid

    def get_exams(self):
        """Lấy danh sách kỳ thi cho Admin (Dùng LEFT JOIN tránh sót bản ghi)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT e.id, e.topic_id, e.title, e.duration_minutes, e.start_time,
                       COALESCE(t.name, 'Chưa gán đề') as topic_name,
                       COUNT(r.id) as participant_count
                FROM exams e
                LEFT JOIN topics t ON e.topic_id = t.id
                LEFT JOIN results r ON e.id = r.exam_id
                GROUP BY e.id
                ORDER BY e.id DESC
            '''
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def delete_exam(self, exam_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
            conn.commit()

    def get_active_exams_for_student(self):
        """Lấy danh sách kỳ thi cho thí sinh tham gia"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT e.id, e.topic_id, e.title, e.duration_minutes, e.start_time,
                       COALESCE(t.name, 'Chưa gán đề') as topic_name,
                       COUNT(q.id) as question_count
                FROM exams e
                LEFT JOIN topics t ON e.topic_id = t.id
                LEFT JOIN questions q ON t.id = q.topic_id
                GROUP BY e.id
                ORDER BY e.id DESC
            '''
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def get_exam_questions(self, topic_id):
        return self.get_questions_by_topic(topic_id)

    # =========================================================================
    # QUẢN LÝ KẾT QUẢ THI (RESULTS) - LƯU VÀ ĐỌC VI PHẠM
    # =========================================================================
    def save_exam_result(self, exam_id, student_name, correct_count, total_questions, score, violations=0):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO results (exam_id, student_name, correct_count, total_questions, score, violations, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (exam_id, student_name, correct_count, total_questions, score, violations, now_str))
            conn.commit()
            return cursor.lastrowid

    def get_exam_results(self, exam_id):
        """Lấy danh sách bảng điểm của một kỳ thi kèm số lần vi phạm"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT id, student_name, correct_count, total_questions, score, violations, completed_at
                FROM results
                WHERE exam_id = ?
                ORDER BY score DESC, completed_at ASC
            '''
            cursor.execute(query, (exam_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_student_result_for_exam(self, exam_id, student_name):
        """Kiểm tra xem thí sinh đã thi ca thi này hay chưa"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT id, score, correct_count, total_questions, violations, completed_at
                FROM results
                WHERE exam_id = ? AND student_name = ?
                ORDER BY id DESC LIMIT 1
            '''
            cursor.execute(query, (exam_id, student_name))
            row = cursor.fetchone()
            return dict(row) if row else None