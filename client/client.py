import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime, timedelta
import threading
import socket
import random
import time
import sys
import os

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_dir not in sys.path:
    sys.path.append(base_dir)

try:
    import client.theme as css
except ModuleNotFoundError:
    import theme as css

from shared.protocol import send_msg, recv_msg

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class StudentExamApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("HỆ THỐNG THI TRỰC TUYẾN • CLIENT")
        self.geometry("1180x760")
        self.minsize(1050, 700)
        self.configure(fg_color=css.COLOR_BG)

        self.sock = None
        self.sock_lock = threading.Lock()
        self.is_connected = False

        self.chat_history = []
        self.username = ""
        self.student_name = ""
        self.server_ip = "192.168.1.26"
        self.server_port = 8888

        self.current_exam = None
        self.questions = []
        self.current_q_index = 0
        self.user_answers = {}
        self.flagged_questions = set()
        self.palette_buttons = {}

        self.saved_exam_history = {} # exam_id -> dict(questions, user_answers)

        self.time_left_seconds = 0
        self.timer_running = False
        self.is_exam_in_progress = False
        self.violation_count = 0
        self._last_violation_time = 0

        self.show_auth_screen()

    def clear_screen(self):
        for w in self.winfo_children():
            w.destroy()

    def ensure_connected(self, host, port):
        if self.sock and self.is_connected:
            return True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((host, port))
            self.sock.settimeout(None)
            self.is_connected = True
            threading.Thread(target=self.receive_loop, daemon=True).start()
            return True
        except Exception as e:
            self.is_connected = False
            return False

    def receive_loop(self):
        while self.is_connected and self.sock:
            try:
                msg = recv_msg(self.sock)
                if not msg:
                    break

                msg_type = msg.get("type")
                status = msg.get("status")

                if msg_type == "LOGIN_OK" and status == "SUCCESS":
                    self.username = msg.get("username", "")
                    self.student_name = msg.get("full_name", "")
                    self.after(0, self.show_exam_lobby)
                elif msg_type == "REGISTER_ACCOUNT_OK":
                    self.after(0, lambda: messagebox.showinfo("Thông báo", msg.get("message", "Đăng ký thành công!")))
                elif status == "ERROR":
                    err_txt = msg.get("message", "Đã xảy ra lỗi!")
                    self.after(0, lambda t=err_txt: self.handle_auth_error(t))
                elif msg_type == "CHAT_BROADCAST":
                    self.chat_history.append(msg)
                    self.after(0, self.append_chat_message, msg)
                elif msg_type == "EXAMS_DATA":
                    exams = msg.get("exams", [])
                    self.after(0, self.render_exam_cards, exams)
                elif msg_type == "QUESTIONS_DATA":
                    self.after(0, self.on_questions_received, msg.get("questions", []))
            except Exception:
                break

    def handle_auth_error(self, err_msg):
        if hasattr(self, 'lbl_auth_err') and self.lbl_auth_err.winfo_exists():
            self.lbl_auth_err.configure(text=err_msg)
        else:
            messagebox.showerror("Lỗi", err_msg)

    # =========================================================================
    # 1. MÀN HÌNH ĐĂNG NHẬP / ĐĂNG KÝ (XÁC THỰC THÍ SINH)
    # =========================================================================
    def show_auth_screen(self):
        self.is_connected = False
        self.is_exam_in_progress = False
        self.clear_screen()

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        card = ctk.CTkFrame(container, width=440, height=560, **css.STYLE_CARD)
        card.pack()
        card.pack_propagate(False)

        badge = ctk.CTkLabel(card, text="CỔNG THI TRỰC TUYẾN", font=css.FONT_BADGE,
                             text_color=css.COLOR_ACCENT, fg_color="#EFF6FF", corner_radius=6, width=160, height=28)
        badge.pack(pady=(25, 6))

        ctk.CTkLabel(card, text="XÁC THỰC THÍ SINH", font=css.FONT_TITLE, text_color=css.COLOR_TEXT_MAIN).pack(pady=(0, 2))
        ctk.CTkLabel(card, text="Đăng nhập tài khoản hoặc tạo mới để vào thi", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(pady=(0, 12))

        self.auth_tab_selector = ctk.CTkSegmentedButton(
            card,
            values=["Đăng Nhập", "Đăng Ký Tài Khoản"],
            command=self.switch_auth_mode,
            width=340,
            height=34
        )
        self.auth_tab_selector.set("Đăng Nhập")
        self.auth_tab_selector.pack(pady=(0, 12))

        ip_box = ctk.CTkFrame(card, fg_color="transparent")
        ip_box.pack(fill="x", padx=45, pady=(0, 6))
        ctk.CTkLabel(ip_box, text="IP Máy Chủ:", font=css.FONT_BADGE, text_color=css.COLOR_TEXT_MUTED).pack(side="left")
        self.in_auth_ip = ctk.CTkEntry(ip_box, width=180, height=28)
        self.in_auth_ip.insert(0, self.server_ip)
        self.in_auth_ip.pack(side="right")

        self.auth_form_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.auth_form_frame.pack(fill="both", expand=True, padx=45)

        self.lbl_auth_err = ctk.CTkLabel(card, text="", font=css.FONT_SUBTITLE, text_color=css.COLOR_DANGER)
        self.lbl_auth_err.pack(pady=(0, 4))

        self.btn_auth_submit = ctk.CTkButton(card, text="Đăng Nhập Ngay", width=350, **css.STYLE_PRIMARY_BTN, command=self.action_submit_auth)
        self.btn_auth_submit.pack(pady=(0, 25))

        self.render_login_form()

    def switch_auth_mode(self, mode):
        self.lbl_auth_err.configure(text="")
        if mode == "Đăng Nhập":
            self.render_login_form()
            self.btn_auth_submit.configure(text="Đăng Nhập Ngay", fg_color=css.COLOR_ACCENT, hover_color="#1D4ED8")
        else:
            self.render_register_form()
            self.btn_auth_submit.configure(text="Tạo Tài Khoản Mới", fg_color=css.COLOR_SUCCESS, hover_color="#15803D")

    def render_login_form(self):
        for w in self.auth_form_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.auth_form_frame, text="Tên đăng nhập:", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w", pady=(4, 2))
        self.in_login_user = ctk.CTkEntry(self.auth_form_frame, placeholder_text="Nhập username...", **css.STYLE_ENTRY)
        self.in_login_user.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(self.auth_form_frame, text="Mật khẩu:", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w", pady=(0, 2))
        self.in_login_pwd = ctk.CTkEntry(self.auth_form_frame, placeholder_text="Nhập mật khẩu...", show="•", **css.STYLE_ENTRY)
        self.in_login_pwd.pack(fill="x", pady=(0, 8))

        self.in_login_pwd.bind("<Return>", lambda e: self.action_submit_auth())

    def render_register_form(self):
        for w in self.auth_form_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.auth_form_frame, text="Họ và Tên đầy đủ:", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w", pady=(2, 1))
        self.in_reg_fullname = ctk.CTkEntry(self.auth_form_frame, placeholder_text="Ví dụ: Nguyễn Văn An", height=32)
        self.in_reg_fullname.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(self.auth_form_frame, text="Tên đăng nhập (Username):", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w", pady=(0, 1))
        self.in_reg_user = ctk.CTkEntry(self.auth_form_frame, placeholder_text="Tên đăng nhập...", height=32)
        self.in_reg_user.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(self.auth_form_frame, text="Mật khẩu:", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w", pady=(0, 1))
        self.in_reg_pwd = ctk.CTkEntry(self.auth_form_frame, placeholder_text="Mật khẩu...", show="•", height=32)
        self.in_reg_pwd.pack(fill="x", pady=(0, 8))

        self.in_reg_pwd.bind("<Return>", lambda e: self.action_submit_auth())

    def action_submit_auth(self):
        self.server_ip = self.in_auth_ip.get().strip()
        if not self.server_ip:
            self.lbl_auth_err.configure(text="Vui lòng nhập IP máy chủ!")
            return

        if not self.ensure_connected(self.server_ip, self.server_port):
            self.lbl_auth_err.configure(text=f"Không thể kết nối đến máy chủ {self.server_ip}!")
            return

        mode = self.auth_tab_selector.get()

        if mode == "Đăng Nhập":
            u = self.in_login_user.get().strip()
            p = self.in_login_pwd.get().strip()
            if not u or not p:
                self.lbl_auth_err.configure(text="Vui lòng điền đầy đủ tên đăng nhập và mật khẩu!")
                return
            with self.sock_lock:
                send_msg(self.sock, {
                    "action": "LOGIN_USER",
                    "username": u,
                    "password": p
                })
        else:
            fn = self.in_reg_fullname.get().strip()
            u = self.in_reg_user.get().strip()
            p = self.in_reg_pwd.get().strip()
            if not fn or not u or not p:
                self.lbl_auth_err.configure(text="Vui lòng điền đủ Họ tên, Username và Mật khẩu!")
                return
            with self.sock_lock:
                send_msg(self.sock, {
                    "action": "REGISTER_ACCOUNT",
                    "username": u,
                    "password": p,
                    "full_name": fn
                })

    # =========================================================================
    # 2. SẢNH CHỜ THI VÀ XEM LẠI LỊCH SỬ ĐỐI CHIẾU
    # =========================================================================
    def show_exam_lobby(self):
        self.is_exam_in_progress = False
        self.clear_screen()

        top_bar = ctk.CTkFrame(self, height=65, fg_color=css.COLOR_CARD, border_width=1, border_color=css.COLOR_BORDER)
        top_bar.pack(fill="x", side="top")

        left_info = ctk.CTkFrame(top_bar, fg_color="transparent")
        left_info.pack(side="left", padx=25, pady=10)
        ctk.CTkLabel(left_info, text="HỆ THỐNG LUYỆN THI TIẾNG ANH", font=css.FONT_SECTION, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(left_info, text=f"Thí sinh: {self.student_name} (@{self.username})", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(anchor="w")

        btn_logout = ctk.CTkButton(top_bar, text="Đăng xuất", width=100, **css.STYLE_DANGER_BTN, command=self.show_auth_screen)
        btn_logout.pack(side="right", padx=25)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=15)

        left_box = ctk.CTkFrame(body, fg_color="transparent")
        left_box.pack(side="left", fill="both", expand=True, padx=(0, 10))

        header_lobby = ctk.CTkFrame(left_box, fg_color="transparent")
        header_lobby.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(header_lobby, text="DANH SÁCH KỲ THI ĐANG MỞ", font=css.FONT_TITLE, text_color=css.COLOR_TEXT_MAIN).pack(side="left")
        ctk.CTkButton(header_lobby, text="🔄 Làm mới", width=100, height=32, font=css.FONT_BADGE, fg_color="#EFF6FF", text_color=css.COLOR_ACCENT, hover_color="#DBEAFE", command=self.request_exam_list).pack(side="right")

        self.scroll_lobby = ctk.CTkScrollableFrame(left_box, **css.STYLE_CARD)
        self.scroll_lobby.pack(fill="both", expand=True)

        right_box = ctk.CTkFrame(body, width=340, **css.STYLE_CARD)
        right_box.pack(side="right", fill="both", padx=(10, 0))
        right_box.pack_propagate(False)

        chat_header = ctk.CTkFrame(right_box, fg_color="#F8FAFC", height=42, corner_radius=10)
        chat_header.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(chat_header, text="💬 TRÒ CHUYỆN VỚI ADMIN", font=css.FONT_BODY_BOLD, text_color=css.COLOR_ACCENT).pack(side="left", padx=10, pady=8)

        self.chat_scroll = ctk.CTkScrollableFrame(right_box, fg_color="transparent")
        self.chat_scroll.pack(fill="both", expand=True, padx=8, pady=4)

        chat_in_row = ctk.CTkFrame(right_box, fg_color="transparent")
        chat_in_row.pack(fill="x", padx=8, pady=(4, 8))

        self.in_chat = ctk.CTkEntry(chat_in_row, placeholder_text="Nhắn tin hỗ trợ...", **css.STYLE_ENTRY)
        self.in_chat.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.in_chat.bind("<Return>", lambda e: self.send_chat_message())

        ctk.CTkButton(chat_in_row, text="Gửi", width=60, **css.STYLE_PRIMARY_BTN, command=self.send_chat_message).pack(side="right")

        for m in self.chat_history:
            self.append_chat_message(m)

        self.request_exam_list()

    def request_exam_list(self):
        for w in self.scroll_lobby.winfo_children():
            w.destroy()
        loading_lbl = ctk.CTkLabel(self.scroll_lobby, text="Đang tải danh sách kỳ thi...", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED)
        loading_lbl.pack(pady=40)

        with self.sock_lock:
            try:
                send_msg(self.sock, {"action": "GET_EXAMS", "student_name": self.student_name})
            except Exception as e:
                loading_lbl.configure(text=f"Lỗi gửi yêu cầu: {e}", text_color=css.COLOR_DANGER)

    def render_exam_cards(self, exams):
        for w in self.scroll_lobby.winfo_children():
            w.destroy()

        if not exams:
            ctk.CTkLabel(self.scroll_lobby, text="Hiện chưa có kỳ thi nào được mở.", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(pady=60)
            return

        now = datetime.now()
        for ex in exams:
            card = ctk.CTkFrame(self.scroll_lobby, fg_color=css.COLOR_CARD_ALT, corner_radius=10, border_width=1, border_color=css.COLOR_BORDER)
            card.pack(fill="x", pady=6, padx=8)

            left_info = ctk.CTkFrame(card, fg_color="transparent")
            left_info.pack(side="left", fill="both", expand=True, padx=16, pady=12)

            ctk.CTkLabel(left_info, text=ex["title"], font=css.FONT_SECTION, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w")
            ctk.CTkLabel(left_info, text=f"📚 Bộ đề: {ex['topic_name']}  |  ⏱ Thời lượng: {ex['duration_minutes']} phút  |  Số câu: {ex['question_count']} câu", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(anchor="w", pady=(2, 4))
            ctk.CTkLabel(left_info, text=f"📅 Bắt đầu: {ex['start_time']}", font=css.FONT_BADGE, text_color=css.COLOR_ACCENT).pack(anchor="w")

            right_action = ctk.CTkFrame(card, fg_color="transparent")
            right_action.pack(side="right", padx=16, pady=12)

            if ex.get("is_completed"):
                badge_done = ctk.CTkLabel(
                    right_action, 
                    text=f"✔ ĐÃ HOÀN THÀNH\nĐiểm: {ex['past_score']}/10 ({ex['past_correct']}/{ex['question_count']} câu)",
                    font=css.FONT_BADGE, text_color="#15803D", fg_color="#DCFCE7", corner_radius=6, padx=10, pady=4
                )
                badge_done.pack(pady=(0, 4))

                btn_history = ctk.CTkButton(
                    right_action, text="🔍 Xem lại bài làm", width=125, height=28,
                    font=css.FONT_BADGE, fg_color="#EFF6FF", text_color=css.COLOR_ACCENT, hover_color="#DBEAFE",
                    command=lambda e_item=ex: self.open_history_review(e_item)
                )
                btn_history.pack()
                continue

            can_start = False
            status_msg = ""
            try:
                st_time = datetime.strptime(ex["start_time"], "%Y-%m-%d %H:%M")
                end_time = st_time + timedelta(minutes=ex["duration_minutes"])
                if now < st_time:
                    status_msg = f"Chưa đến giờ\n(Mở lúc {st_time.strftime('%H:%M')})"
                elif now > end_time:
                    status_msg = "Đã kết thúc"
                else:
                    can_start = True
            except Exception:
                can_start = True

            if can_start:
                btn_join = ctk.CTkButton(right_action, text="VÀO THI NGAY", width=130, **css.STYLE_PRIMARY_BTN, command=lambda e_item=ex: self.start_taking_exam(e_item))
                btn_join.pack()
            else:
                ctk.CTkLabel(right_action, text=status_msg, font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MUTED, justify="center").pack()

    def open_history_review(self, exam_item):
        self.current_exam = exam_item
        history = self.saved_exam_history.get(exam_item["id"])
        if history:
            self.questions = history["questions"]
            self.user_answers = history["user_answers"]
            self.show_review_screen()
        else:
            with self.sock_lock:
                send_msg(self.sock, {"action": "GET_QUESTIONS", "topic_id": exam_item["topic_id"]})
            self._pending_review_exam = exam_item

    def send_chat_message(self):
        text = self.in_chat.get().strip()
        if not text or not self.sock:
            return
        try:
            with self.sock_lock:
                send_msg(self.sock, {
                    "action": "SEND_CHAT",
                    "sender": self.student_name,
                    "text": text
                })
            self.in_chat.delete(0, "end")
        except Exception:
            pass

    def append_chat_message(self, msg):
        if not hasattr(self, 'chat_scroll') or not self.chat_scroll.winfo_exists():
            return

        sender = msg.get("sender", "")
        text = msg.get("text", "")
        send_time = msg.get("time", "")

        is_me = (sender == self.student_name)
        is_admin = ("Admin" in sender or "HỆ THỐNG" in sender)

        msg_box = ctk.CTkFrame(self.chat_scroll, fg_color=css.COLOR_CARD_ALT, corner_radius=8, border_width=1, border_color=css.COLOR_BORDER)
        msg_box.pack(fill="x", pady=3, padx=2)

        if is_admin:
            msg_box.configure(fg_color="#EFF6FF", border_color="#BFDBFE")
            ctk.CTkLabel(msg_box, text=f"👑 {sender} ({send_time})", font=css.FONT_BODY_BOLD, text_color=css.COLOR_ACCENT).pack(anchor="w", padx=8, pady=(4, 1))
            ctk.CTkLabel(msg_box, text=text, font=css.FONT_BODY, text_color=css.COLOR_TEXT_MAIN, wraplength=280, justify="left").pack(anchor="w", padx=8, pady=(0, 4))
        elif is_me:
            msg_box.configure(fg_color="#F0FDF4", border_color="#BBF7D0")
            ctk.CTkLabel(msg_box, text=f"Bạn ({send_time})", font=css.FONT_BODY_BOLD, text_color="#15803D").pack(anchor="w", padx=8, pady=(4, 1))
            ctk.CTkLabel(msg_box, text=text, font=css.FONT_BODY, text_color=css.COLOR_TEXT_MAIN, wraplength=280, justify="left").pack(anchor="w", padx=8, pady=(0, 4))
        else:
            ctk.CTkLabel(msg_box, text=f"{sender} ({send_time})", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MUTED).pack(anchor="w", padx=8, pady=(4, 1))
            ctk.CTkLabel(msg_box, text=text, font=css.FONT_BODY, text_color=css.COLOR_TEXT_MAIN, wraplength=280, justify="left").pack(anchor="w", padx=8, pady=(0, 4))

    # =========================================================================
    # 3. TRÁO CÂU HỎI & ĐÁP ÁN (SHUFFLE)
    # =========================================================================
    def shuffle_exam_questions(self, raw_questions):
        processed_questions = []

        for q in raw_questions:
            q_copy = dict(q)
            orig_correct = q_copy.get("correct_answer", "").strip().upper()
            orig_opts = {
                "A": q_copy.get("option_a", ""),
                "B": q_copy.get("option_b", ""),
                "C": q_copy.get("option_c", ""),
                "D": q_copy.get("option_d", "")
            }
            correct_text = orig_opts.get(orig_correct, "")

            opt_texts = [q_copy["option_a"], q_copy["option_b"], q_copy["option_c"], q_copy["option_d"]]
            random.shuffle(opt_texts)

            labels = ["A", "B", "C", "D"]
            new_correct = orig_correct
            for lbl, txt in zip(labels, opt_texts):
                q_copy[f"option_{lbl.lower()}"] = txt
                if txt == correct_text:
                    new_correct = lbl

            q_copy["correct_answer"] = new_correct
            processed_questions.append(q_copy)

        standalone_qs = []
        passage_groups = {}

        for q in processed_questions:
            p = q.get("passage")
            if p and p.strip():
                passage_groups.setdefault(p, []).append(q)
            else:
                standalone_qs.append(q)

        all_blocks = [[q] for q in standalone_qs] + list(passage_groups.values())
        random.shuffle(all_blocks)

        shuffled_final = []
        for block in all_blocks:
            shuffled_final.extend(block)

        return shuffled_final

    # =========================================================================
    # 4. PHÒNG THI & CHỐNG GIAN LẬN NATIVE WINDOWS API
    # =========================================================================
    def start_taking_exam(self, exam_item):
        self._pending_review_exam = None
        self.current_exam = exam_item
        with self.sock_lock:
            send_msg(self.sock, {"action": "GET_QUESTIONS", "topic_id": exam_item["topic_id"]})

    def on_questions_received(self, questions):
        if not questions:
            messagebox.showwarning("Thông báo", "Kỳ thi này hiện chưa có nội dung câu hỏi!")
            return

        if getattr(self, '_pending_review_exam', None):
            self.questions = questions
            self.user_answers = {}
            self._pending_review_exam = None
            self.show_review_screen()
            return

        self.questions = self.shuffle_exam_questions(questions)
        self.current_q_index = 0
        self.user_answers = {}
        self.flagged_questions = set()
        self.violation_count = 0
        self._last_violation_time = 0

        try:
            dur = int(self.current_exam["duration_minutes"])
        except (ValueError, TypeError):
            dur = 15
        self.time_left_seconds = dur * 60
        self.is_exam_in_progress = True

        with self.sock_lock:
            send_msg(self.sock, {
                "action": "START_EXAM_STATUS",
                "student_name": self.student_name,
                "exam_title": self.current_exam["title"],
                "time_left": self.time_left_seconds
            })

        self.render_arena_ui()
        self.start_timer_thread()
        self.bind("<FocusOut>", self.on_window_focus_out)

    def on_window_focus_out(self, event=None):
        if not self.is_exam_in_progress:
            return

        now = time.time()
        last_time = getattr(self, '_last_violation_time', 0)
        if now - last_time < 1.5:
            return

        try:
            import ctypes
            hwnd_active = ctypes.windll.user32.GetForegroundWindow()
            hwnd_app = self.winfo_id()
            hwnd_root = ctypes.windll.user32.GetAncestor(hwnd_app, 2)

            if hwnd_active in (hwnd_app, hwnd_root):
                return
        except Exception:
            if event and event.widget != self:
                return

        self._last_violation_time = now
        self.violation_count += 1
        
        if hasattr(self, 'lbl_cheat_warning') and self.lbl_cheat_warning.winfo_exists():
            self.lbl_cheat_warning.configure(
                text=f"⚠ CẢNH BÁO GIAN LẬN ({self.violation_count} LẦN): BẠN VỪA RỜI KHỎI MÀN HÌNH LÀM BÀI!",
                fg_color="#FEE2E2", text_color="#DC2626"
            )

        with self.sock_lock:
            try:
                send_msg(self.sock, {
                    "action": "REPORT_VIOLATION",
                    "student_name": self.student_name,
                    "violations": self.violation_count
                })
            except Exception:
                pass

    def render_arena_ui(self):
        self.clear_screen()

        top_bar = ctk.CTkFrame(self, height=65, fg_color=css.COLOR_CARD, border_width=1, border_color=css.COLOR_BORDER)
        top_bar.pack(fill="x", side="top")

        left_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        left_box.pack(side="left", padx=25, pady=10)
        ctk.CTkLabel(left_box, text=self.current_exam["title"], font=css.FONT_SECTION, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(left_box, text=f"Thí sinh: {self.student_name}", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(anchor="w")

        mins, secs = divmod(self.time_left_seconds, 60)
        self.lbl_clock = ctk.CTkLabel(top_bar, text=f"⏱ {mins:02d}:{secs:02d}", font=("Segoe UI", 16, "bold"), text_color=css.COLOR_ACCENT)
        self.lbl_clock.pack(side="left", expand=True)

        ctk.CTkButton(top_bar, text="NỘP BÀI THI", width=120, height=36, font=css.FONT_BODY_BOLD, fg_color=css.COLOR_DANGER, hover_color="#B91C1C", command=self.confirm_finish_exam).pack(side="right", padx=25)

        self.lbl_cheat_warning = ctk.CTkLabel(self, text="🛡 Chế độ giám sát thi đang bật: Vui lòng không chuyển tab hoặc thoát ứng dụng.", font=("Segoe UI", 11, "bold"), text_color="#15803D", fg_color="#DCFCE7", height=28)
        self.lbl_cheat_warning.pack(fill="x", padx=20, pady=(5, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=8)

        palette_panel = ctk.CTkFrame(body, width=260, **css.STYLE_CARD)
        palette_panel.pack(side="right", fill="y", padx=(10, 0))
        palette_panel.pack_propagate(False)

        ctk.CTkLabel(palette_panel, text="📌 DANH SÁCH CÂU HỎI", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w", padx=12, pady=(10, 4))
        
        guide_box = ctk.CTkFrame(palette_panel, fg_color="#F8FAFC", corner_radius=6)
        guide_box.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkLabel(guide_box, text="🟢 Đã làm   ⚪ Chưa làm   🚩 Cần xem lại", font=("Segoe UI", 10), text_color=css.COLOR_TEXT_MUTED).pack(pady=4)

        self.palette_scroll = ctk.CTkScrollableFrame(palette_panel, fg_color="transparent")
        self.palette_scroll.pack(fill="both", expand=True, padx=8, pady=4)

        self.palette_buttons = {}
        cols = 4
        for i in range(len(self.questions)):
            r = i // cols
            c = i % cols
            btn = ctk.CTkButton(
                self.palette_scroll, text=str(i + 1), width=48, height=36,
                font=css.FONT_BADGE, corner_radius=6, border_width=1,
                border_color=css.COLOR_BORDER, fg_color=css.COLOR_CARD_ALT,
                text_color=css.COLOR_TEXT_MAIN, hover_color="#DBEAFE",
                command=lambda idx=i: self.jump_to_question(idx)
            )
            btn.grid(row=r, column=c, padx=3, pady=3)
            self.palette_buttons[i] = btn

        left_arena = ctk.CTkFrame(body, fg_color="transparent")
        left_arena.pack(side="left", fill="both", expand=True)

        nav_bar = ctk.CTkFrame(left_arena, fg_color="transparent", height=45)
        nav_bar.pack(fill="x", side="bottom", pady=(10, 0))

        self.btn_prev = ctk.CTkButton(nav_bar, text="◀ Câu trước đó", width=130, height=36, font=css.FONT_BODY_BOLD, fg_color="#E2E8F0", text_color=css.COLOR_TEXT_MAIN, hover_color="#CBD5E1", command=self.prev_question)
        self.btn_prev.pack(side="left")

        self.btn_flag = ctk.CTkButton(nav_bar, text="🚩 Đánh dấu xem lại", width=150, height=36, font=css.FONT_BODY_BOLD, fg_color="#FEF3C7", text_color="#D97706", hover_color="#FDE68A", command=self.toggle_flag_current_question)
        self.btn_flag.pack(side="left", padx=15)

        self.btn_next = ctk.CTkButton(nav_bar, text="Câu tiếp theo ▶", width=140, **css.STYLE_PRIMARY_BTN, command=self.next_question)
        self.btn_next.pack(side="right")

        self.arena_content = ctk.CTkFrame(left_arena, fg_color="transparent")
        self.arena_content.pack(fill="both", expand=True)

        self.passage_display_box = ctk.CTkFrame(self.arena_content, **css.STYLE_CARD)
        ctk.CTkLabel(self.passage_display_box, text="📖 NỘI DUNG ĐOẠN VĂN (READING PASSAGE)", font=css.FONT_BODY_BOLD, text_color=css.COLOR_ACCENT).pack(anchor="w", padx=15, pady=(10, 4))
        self.txt_passage_viewer = ctk.CTkTextbox(self.passage_display_box, font=("Segoe UI", 13), activate_scrollbars=True, wrap="word")
        self.txt_passage_viewer.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        self.question_display_box = ctk.CTkFrame(self.arena_content, **css.STYLE_CARD)
        self.lbl_q_step = ctk.CTkLabel(self.question_display_box, text="", font=css.FONT_BADGE, text_color=css.COLOR_ACCENT)
        self.lbl_q_step.pack(anchor="w", padx=20, pady=(12, 4))

        self.lbl_question_content = ctk.CTkLabel(self.question_display_box, text="", font=css.FONT_SECTION, text_color=css.COLOR_TEXT_MAIN, wraplength=480, justify="left")
        self.lbl_question_content.pack(anchor="w", padx=20, pady=(0, 10))

        self.opt_buttons = {}
        for opt in ["A", "B", "C", "D"]:
            btn = ctk.CTkButton(
                self.question_display_box, text="", height=44, anchor="w",
                font=css.FONT_BODY, corner_radius=8, border_width=1,
                border_color=css.COLOR_BORDER, fg_color=css.COLOR_CARD_ALT,
                text_color=css.COLOR_TEXT_MAIN, hover_color="#E2E8F0",
                command=lambda o=opt: self.select_option(o)
            )
            btn.pack(fill="x", padx=20, pady=4)
            self.opt_buttons[opt] = btn

        self.display_current_question()

    def jump_to_question(self, index):
        self.current_q_index = index
        self.display_current_question()

    def toggle_flag_current_question(self):
        if self.current_q_index in self.flagged_questions:
            self.flagged_questions.remove(self.current_q_index)
        else:
            self.flagged_questions.add(self.current_q_index)
        self.update_palette_colors()
        self.update_flag_button_ui()

    def update_flag_button_ui(self):
        if self.current_q_index in self.flagged_questions:
            self.btn_flag.configure(text="🚩 Đã gắn cờ (Bỏ cờ)", fg_color="#F59E0B", text_color="#FFFFFF", hover_color="#D97706")
        else:
            self.btn_flag.configure(text="🚩 Đánh dấu xem lại", fg_color="#FEF3C7", text_color="#D97706", hover_color="#FDE68A")

    def update_palette_colors(self):
        for idx, btn in self.palette_buttons.items():
            is_active = (idx == self.current_q_index)
            is_flagged = (idx in self.flagged_questions)
            has_answered = (idx in self.user_answers)

            btn.configure(border_color=css.COLOR_ACCENT if is_active else css.COLOR_BORDER, border_width=2 if is_active else 1)

            if is_flagged:
                btn.configure(fg_color="#FDE68A", text_color="#B45309", text=f"🚩{idx+1}")
            elif has_answered:
                btn.configure(fg_color="#DCFCE7", text_color="#15803D", text=str(idx+1))
            else:
                btn.configure(fg_color=css.COLOR_CARD_ALT, text_color=css.COLOR_TEXT_MAIN, text=str(idx+1))

    def display_current_question(self):
        q = self.questions[self.current_q_index]
        total = len(self.questions)
        self.lbl_q_step.configure(text=f"CÂU HỎI {self.current_q_index + 1} / {total}")
        self.lbl_question_content.configure(text=q["question"])

        passage = q.get("passage")
        if passage and passage.strip():
            self.passage_display_box.pack(side="left", fill="both", expand=True, padx=(0, 10))
            self.txt_passage_viewer.configure(state="normal")
            self.txt_passage_viewer.delete("1.0", "end")
            self.txt_passage_viewer.insert("1.0", passage)
            self.txt_passage_viewer.configure(state="disabled")

            self.question_display_box.pack(side="right", fill="both", expand=True)
            self.lbl_question_content.configure(wraplength=420)
        else:
            self.passage_display_box.pack_forget()
            self.question_display_box.pack(fill="both", expand=True)
            self.lbl_question_content.configure(wraplength=700)

        options_map = {
            "A": f"A.  {q['option_a']}",
            "B": f"B.  {q['option_b']}",
            "C": f"C.  {q['option_c']}",
            "D": f"D.  {q['option_d']}",
        }

        chosen = self.user_answers.get(self.current_q_index, None)
        for code, btn in self.opt_buttons.items():
            btn.configure(text=f"   {options_map[code]}")
            if chosen == code:
                btn.configure(fg_color="#DBEAFE", border_color=css.COLOR_ACCENT, text_color=css.COLOR_ACCENT)
            else:
                btn.configure(fg_color=css.COLOR_CARD_ALT, border_color=css.COLOR_BORDER, text_color=css.COLOR_TEXT_MAIN)

        self.btn_prev.configure(state="normal" if self.current_q_index > 0 else "disabled")
        if self.current_q_index == total - 1:
            self.btn_next.configure(text="Xem tổng kết")
        else:
            self.btn_next.configure(text="Câu tiếp theo ▶")

        self.update_palette_colors()
        self.update_flag_button_ui()

    def select_option(self, opt_code):
        self.user_answers[self.current_q_index] = opt_code
        self.display_current_question()

    def prev_question(self):
        if self.current_q_index > 0:
            self.current_q_index -= 1
            self.display_current_question()

    def next_question(self):
        if self.current_q_index < len(self.questions) - 1:
            self.current_q_index += 1
            self.display_current_question()
        else:
            self.confirm_finish_exam()

    # =========================================================================
    # 5. BỘ ĐẾM GIỜ & GỬI HEARTBEAT
    # =========================================================================
    def start_timer_thread(self):
        self.timer_running = True
        threading.Thread(target=self.timer_loop, daemon=True).start()

    def timer_loop(self):
        hb_tick = 0
        while self.timer_running and self.time_left_seconds > 0:
            time.sleep(1)
            self.time_left_seconds -= 1
            hb_tick += 1

            self.after(0, self.update_clock_ui)

            if hb_tick >= 3 and self.is_exam_in_progress:
                hb_tick = 0
                with self.sock_lock:
                    try:
                        send_msg(self.sock, {
                            "action": "HEARTBEAT",
                            "student_name": self.student_name,
                            "time_left": self.time_left_seconds
                        })
                    except Exception:
                        pass

        if self.timer_running and self.time_left_seconds <= 0:
            self.after(0, self.time_out_auto_submit)

    def update_clock_ui(self):
        if not hasattr(self, 'lbl_clock') or not self.lbl_clock.winfo_exists():
            return
        mins, secs = divmod(self.time_left_seconds, 60)
        self.lbl_clock.configure(text=f"⏱ {mins:02d}:{secs:02d}")
        if self.time_left_seconds < 120:
            self.lbl_clock.configure(text_color=css.COLOR_DANGER)

    def time_out_auto_submit(self):
        self.timer_running = False
        messagebox.showinfo("Hết giờ", "Thời gian làm bài đã kết thúc! Hệ thống sẽ tự động nộp bài.")
        self.calculate_and_show_result()

    def confirm_finish_exam(self):
        answered = len(self.user_answers)
        total = len(self.questions)
        flag_cnt = len(self.flagged_questions)
        flag_info = f"\n(Có {flag_cnt} câu đang gắn cờ phân vân)" if flag_cnt > 0 else ""

        if messagebox.askyesno("Nộp bài thi", f"Bạn đã làm {answered}/{total} câu hỏi.{flag_info}\nBạn có chắc chắn muốn nộp bài thi ngay không?"):
            self.timer_running = False
            self.calculate_and_show_result()

    # =========================================================================
    # 6. TỔNG KẾT, GỬI VI PHẠM & XEM LẠI CHI TIẾT
    # =========================================================================
    def calculate_and_show_result(self):
        self.is_exam_in_progress = False
        self.unbind("<FocusOut>")
        self.clear_screen()

        correct_count = 0
        total = len(self.questions)

        for idx, q in enumerate(self.questions):
            ans = self.user_answers.get(idx, None)
            if ans == q["correct_answer"]:
                correct_count += 1

        score_10 = round((correct_count / total) * 10, 1) if total > 0 else 0

        self.saved_exam_history[self.current_exam["id"]] = {
            "questions": list(self.questions),
            "user_answers": dict(self.user_answers)
        }

        # Gửi kèm số lần vi phạm thực tế vào Database
        try:
            with self.sock_lock:
                send_msg(self.sock, {
                    "action": "SUBMIT_EXAM",
                    "exam_id": self.current_exam["id"],
                    "student_name": self.student_name,
                    "correct_count": correct_count,
                    "total_questions": total,
                    "score": score_10,
                    "violations": self.violation_count
                })
        except Exception as e:
            print("[-] Gửi kết quả thất bại:", e)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        card = ctk.CTkFrame(container, width=540, height=480, **css.STYLE_CARD)
        card.pack()
        card.pack_propagate(False)

        badge_txt = "XUẤT SẮC" if score_10 >= 8 else ("ĐẠT YÊU CẦU" if score_10 >= 5 else "CẦN CỐ GẮNG")
        badge_bg = "#DCFCE7" if score_10 >= 8 else ("#EFF6FF" if score_10 >= 5 else "#FEE2E2")
        badge_fg = "#15803D" if score_10 >= 8 else ("#1D4ED8" if score_10 >= 5 else "#B91C1C")

        ctk.CTkLabel(card, text=badge_txt, font=css.FONT_BADGE, text_color=badge_fg, fg_color=badge_bg, corner_radius=6, width=140, height=28).pack(pady=(35, 10))

        ctk.CTkLabel(card, text="KẾT QUẢ BÀI THI", font=css.FONT_TITLE, text_color=css.COLOR_TEXT_MAIN).pack(pady=(0, 4))
        ctk.CTkLabel(card, text=f"Kỳ thi: {self.current_exam['title']}", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(pady=(0, 15))

        ctk.CTkLabel(card, text=f"{score_10} / 10", font=("Segoe UI", 38, "bold"), text_color=css.COLOR_ACCENT).pack(pady=(0, 8))
        ctk.CTkLabel(card, text=f"Số câu trả lời đúng: {correct_count} / {total} câu", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(pady=(0, 25))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=40)

        btn_review = ctk.CTkButton(btn_row, text="🔍 Xem Lại Chi Tiết Bài Làm", width=200, height=40, font=css.FONT_BODY_BOLD, fg_color="#F1F5F9", text_color=css.COLOR_TEXT_MAIN, hover_color="#E2E8F0", command=self.show_review_screen)
        btn_review.pack(side="left", padx=5, expand=True)

        btn_lobby = ctk.CTkButton(btn_row, text="Quay lại sảnh thi", width=180, **css.STYLE_PRIMARY_BTN, command=self.show_exam_lobby)
        btn_lobby.pack(side="right", padx=5, expand=True)

    def show_review_screen(self):
        self.clear_screen()

        top_bar = ctk.CTkFrame(self, height=65, fg_color=css.COLOR_CARD, border_width=1, border_color=css.COLOR_BORDER)
        top_bar.pack(fill="x", side="top")

        left_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        left_box.pack(side="left", padx=25, pady=10)
        ctk.CTkLabel(left_box, text=f"XEM LẠI CHI TIẾT: {self.current_exam['title']}", font=css.FONT_SECTION, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(left_box, text="Đối chiếu bài làm của bạn với đáp án chính xác", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(anchor="w")

        ctk.CTkButton(top_bar, text="Trở về Sảnh", width=120, **css.STYLE_PRIMARY_BTN, command=self.show_exam_lobby).pack(side="right", padx=25)

        scroll_review = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_review.pack(fill="both", expand=True, padx=30, pady=15)

        grouped_items = []
        current_passage = None
        current_group = []

        for idx, q in enumerate(self.questions):
            q_with_idx = dict(q)
            q_with_idx["_global_idx"] = idx
            p = q.get("passage")
            p_clean = p.strip() if p else ""
            if p_clean:
                if p_clean == current_passage:
                    current_group.append(q_with_idx)
                else:
                    if current_group:
                        grouped_items.append({"passage": current_passage, "questions": current_group})
                    current_passage = p_clean
                    current_group = [q_with_idx]
            else:
                if current_group:
                    grouped_items.append({"passage": current_passage, "questions": current_group})
                    current_passage = None
                    current_group = []
                grouped_items.append({"passage": None, "questions": [q_with_idx]})

        if current_group:
            grouped_items.append({"passage": current_passage, "questions": current_group})

        for block in grouped_items:
            passage_text = block["passage"]
            sub_qs = block["questions"]

            if passage_text:
                container_card = ctk.CTkFrame(scroll_review, fg_color="#F8FAFC", corner_radius=10, border_width=1.5, border_color="#CBD5E1")
                container_card.pack(fill="x", pady=8, padx=5)

                header_p = ctk.CTkFrame(container_card, fg_color="#EFF6FF", corner_radius=8)
                header_p.pack(fill="x", padx=10, pady=(10, 6))

                ctk.CTkLabel(header_p, text="📖 ĐOẠN VĂN BÀI ĐỌC (READING PASSAGE):", font=css.FONT_BODY_BOLD, text_color=css.COLOR_ACCENT).pack(anchor="w", padx=12, pady=(8, 2))
                ctk.CTkLabel(header_p, text=passage_text, font=("Segoe UI", 12), text_color=css.COLOR_TEXT_MAIN, wraplength=880, justify="left").pack(anchor="w", padx=12, pady=(0, 10))

                for q_item in sub_qs:
                    self.render_review_question_card(container_card, q_item, is_sub=True)
            else:
                for q_item in sub_qs:
                    self.render_review_question_card(scroll_review, q_item, is_sub=False)

    def render_review_question_card(self, parent, q, is_sub=False):
        g_idx = q["_global_idx"]
        chosen = self.user_answers.get(g_idx, None)
        correct = q["correct_answer"].strip().upper()
        is_correct = (chosen == correct)

        card_border = "#BBF7D0" if is_correct else ("#E2E8F0" if not chosen else "#FECACA")
        card_bg = "#FFFFFF"
        card = ctk.CTkFrame(parent, fg_color=card_bg, corner_radius=8 if is_sub else 10, border_width=1 if is_sub else 1.5, border_color=card_border)
        card.pack(fill="x", pady=4 if is_sub else 8, padx=10 if is_sub else 5)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(10, 4))

        status_text = "✔ ĐÚNG" if is_correct else ("Chưa chọn" if not chosen else "✖ SAI")
        status_color = "#15803D" if is_correct else ("#64748B" if not chosen else "#DC2626")
        status_bg = "#DCFCE7" if is_correct else ("#F1F5F9" if not chosen else "#FEE2E2")

        ctk.CTkLabel(header, text=f"Câu {g_idx + 1}: {q['question']}", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN, wraplength=760, justify="left").pack(side="left")
        ctk.CTkLabel(header, text=status_text, font=css.FONT_BADGE, text_color=status_color, fg_color=status_bg, corner_radius=6, width=80, height=24).pack(side="right")

        opts = {
            "A": q["option_a"],
            "B": q["option_b"],
            "C": q["option_c"],
            "D": q["option_d"]
        }

        opts_frame = ctk.CTkFrame(card, fg_color="transparent")
        opts_frame.pack(fill="x", padx=16, pady=(0, 10))

        for key, val in opts.items():
            row_opt = ctk.CTkFrame(opts_frame, fg_color="transparent")
            row_opt.pack(fill="x", pady=2)

            prefix = f"{key}. {val}"
            lbl_color = css.COLOR_TEXT_MAIN
            badge_note = ""

            if key == correct:
                lbl_color = "#15803D"
                badge_note = "  (✔ Đáp án đúng chuẩn)"
            if key == chosen:
                if not is_correct:
                    lbl_color = "#DC2626"
                    badge_note += "  [✖ Bạn đã chọn đáp án này]"
                else:
                    badge_note += "  [✔ Bạn đã chọn đúng]"

            ctk.CTkLabel(row_opt, text=f"{prefix}{badge_note}", font=css.FONT_BODY, text_color=lbl_color).pack(side="left")

if __name__ == "__main__":
    app = StudentExamApp()
    app.mainloop()