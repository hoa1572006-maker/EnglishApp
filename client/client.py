import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime, timedelta
import threading
import socket
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
        self.geometry("1060x700")
        self.minsize(980, 640)
        self.configure(fg_color=css.COLOR_BG)

        # Socket chính xử lý đề thi
        self.sock = None
        # Socket phụ chuyên xử lý khung chat
        self.chat_sock = None
        self.is_chat_running = False
        self.chat_history = []

        self.student_name = ""
        self.server_ip = "172.26.78.184"
        self.server_port = 8888

        self.current_exam = None
        self.questions = []
        self.current_q_index = 0
        self.user_answers = {}
        self.time_left_seconds = 0
        self.timer_running = False

        self.show_login_screen()

    def clear_screen(self):
        for w in self.winfo_children():
            w.destroy()

    def connect_server(self, host, port):
        # 1. Socket dữ liệu thi
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5.0)
        self.sock.connect((host, port))
        self.sock.settimeout(None)

        # 2. Socket trò chuyện
        if self.chat_sock:
            try:
                self.chat_sock.close()
            except Exception:
                pass
        try:
            self.chat_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.chat_sock.connect((host, port))
            send_msg(self.chat_sock, {"action": "REGISTER_USER", "student_name": self.student_name})
            
            self.is_chat_running = True
            threading.Thread(target=self.listen_chat_loop, daemon=True).start()
        except Exception as e:
            print("[-] Không thể mở socket chat:", e)

    def listen_chat_loop(self):
        while self.is_chat_running and self.chat_sock:
            try:
                msg = recv_msg(self.chat_sock)
                if not msg:
                    break
                if msg.get("type") == "CHAT_BROADCAST":
                    self.chat_history.append(msg)
                    self.after(0, self.append_chat_message, msg)
            except Exception:
                break

    # =========================================================================
    # 1. MÀN HÌNH ĐĂNG NHẬP
    # =========================================================================
    def show_login_screen(self):
        self.is_chat_running = False
        self.clear_screen()
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        card = ctk.CTkFrame(container, width=440, height=480, **css.STYLE_CARD)
        card.pack()
        card.pack_propagate(False)

        badge = ctk.CTkLabel(card, text="CỔNG THI TRỰC TUYẾN", font=css.FONT_BADGE,
                             text_color=css.COLOR_ACCENT, fg_color="#EFF6FF", corner_radius=6, width=160, height=28)
        badge.pack(pady=(30, 8))

        ctk.CTkLabel(card, text="ĐĂNG NHẬP THÍ SINH", font=css.FONT_TITLE, text_color=css.COLOR_TEXT_MAIN).pack(pady=(0, 4))
        ctk.CTkLabel(card, text="Nhập thông tin kết nối phòng thi", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(pady=(0, 20))

        self.in_name = ctk.CTkEntry(card, placeholder_text="Họ và Tên thí sinh...", width=340, **css.STYLE_ENTRY)
        self.in_name.pack(pady=8)

        self.in_ip = ctk.CTkEntry(card, placeholder_text="IP Server...", width=340, **css.STYLE_ENTRY)
        self.in_ip.insert(0, self.server_ip)
        self.in_ip.pack(pady=8)

        self.lbl_login_err = ctk.CTkLabel(card, text="", font=css.FONT_SUBTITLE, text_color=css.COLOR_DANGER)
        self.lbl_login_err.pack()

        btn_enter = ctk.CTkButton(card, text="KẾT NỐI & VÀO SẢNH THI ➔", width=340, **css.STYLE_PRIMARY_BTN, command=self.handle_enter_lobby)
        btn_enter.pack(pady=(15, 10))

    def handle_enter_lobby(self):
        name = self.in_name.get().strip()
        ip = self.in_ip.get().strip()
        if not name or not ip:
            self.lbl_login_err.configure(text="Vui lòng điền đủ họ tên và IP Server!")
            return

        self.student_name = name
        self.server_ip = ip
        try:
            self.connect_server(ip, self.server_port)
            self.show_exam_lobby()
        except Exception:
            self.lbl_login_err.configure(text=f"Không thể kết nối đến máy chủ ({ip})!")

    # =========================================================================
    # 2. SẢNH CHỜ THI (LOBBY + CHAT)
    # =========================================================================
    def show_exam_lobby(self):
        self.clear_screen()

        top_bar = ctk.CTkFrame(self, height=65, fg_color=css.COLOR_CARD, border_width=1, border_color=css.COLOR_BORDER)
        top_bar.pack(fill="x", side="top")

        ctk.CTkLabel(top_bar, text=f"👤 Thí sinh: {self.student_name}  •  IP Server: {self.server_ip}", font=css.FONT_SECTION, text_color=css.COLOR_TEXT_MAIN).pack(side="left", padx=25)
        
        btn_logout = ctk.CTkButton(top_bar, text="Thoát", width=80, height=30, fg_color="#F1F5F9", text_color=css.COLOR_TEXT_MAIN, hover_color="#E2E8F0", font=css.FONT_BADGE, command=self.show_login_screen)
        btn_logout.pack(side="right", padx=25)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=15)

        # Cột bên trái: Danh sách đề thi
        left_box = ctk.CTkFrame(body, fg_color="transparent")
        left_box.pack(side="left", fill="both", expand=True, padx=(0, 10))

        header_lobby = ctk.CTkFrame(left_box, fg_color="transparent")
        header_lobby.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(header_lobby, text="DANH SÁCH KỲ THI ĐANG MỞ", font=css.FONT_TITLE, text_color=css.COLOR_TEXT_MAIN).pack(side="left")
        ctk.CTkButton(header_lobby, text="🔄 Làm mới", width=100, height=32, font=css.FONT_BADGE, fg_color="#EFF6FF", text_color=css.COLOR_ACCENT, hover_color="#DBEAFE", command=self.show_exam_lobby).pack(side="right")

        self.scroll_lobby = ctk.CTkScrollableFrame(left_box, **css.STYLE_CARD)
        self.scroll_lobby.pack(fill="both", expand=True)

        # Cột bên phải: Khung Chat
        right_box = ctk.CTkFrame(body, width=340, **css.STYLE_CARD)
        right_box.pack(side="right", fill="both", padx=(10, 0))
        right_box.pack_propagate(False)

        chat_header = ctk.CTkFrame(right_box, fg_color="#F8FAFC", height=42, corner_radius=10)
        chat_header.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(chat_header, text="💬 TRÒ CHUYỆN VỚI ADMIN", font=css.FONT_BODY_BOLD, text_color=css.COLOR_ACCENT).pack(side="left", padx=12, pady=8)

        self.chat_scroll = ctk.CTkScrollableFrame(right_box, fg_color="transparent")
        self.chat_scroll.pack(fill="both", expand=True, padx=8, pady=4)

        # Vẽ lại các tin nhắn cũ đã nhận
        for old_msg in self.chat_history:
            self.append_chat_message(old_msg)

        chat_input_row = ctk.CTkFrame(right_box, fg_color="transparent")
        chat_input_row.pack(fill="x", padx=8, pady=(4, 8))

        self.in_chat = ctk.CTkEntry(chat_input_row, placeholder_text="Nhập tin nhắn...", height=36, font=css.FONT_BODY)
        self.in_chat.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.in_chat.bind("<Return>", lambda e: self.send_chat_message())

        btn_send = ctk.CTkButton(chat_input_row, text="Gửi", width=60, height=36, font=css.FONT_BODY_BOLD, fg_color=css.COLOR_ACCENT, hover_color="#1D4ED8", command=self.send_chat_message)
        btn_send.pack(side="right")

        # Tải dữ liệu kỳ thi trực tiếp qua socket dữ liệu
        try:
            send_msg(self.sock, {"action": "GET_EXAMS", "student_name": self.student_name})
            res = recv_msg(self.sock)
            exams = res.get("exams", [])
        except Exception:
            ctk.CTkLabel(self.scroll_lobby, text="Mất kết nối với Server!", font=css.FONT_SUBTITLE, text_color=css.COLOR_DANGER).pack(pady=40)
            return

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
                    font=css.FONT_BADGE, text_color="#15803D", fg_color="#DCFCE7", corner_radius=8, padx=12, pady=6
                )
                badge_done.pack()
                continue

            can_enter = False
            status_msg = ""
            try:
                start_dt = datetime.strptime(ex["start_time"], "%Y-%m-%d %H:%M")
                dur_val = int(ex.get("duration_minutes", 15))
                end_dt = start_dt + timedelta(minutes=dur_val)
                if now < start_dt:
                    can_enter = False
                    status_msg = f"Chưa tới giờ thi\n({ex['start_time'].split(' ')[1]})"
                elif start_dt <= now <= end_dt:
                    can_enter = True
                    status_msg = "ĐANG DIỄN RA"
                else:
                    can_enter = False
                    status_msg = "ĐÃ HẾT GIỜ"
            except Exception:
                can_enter = True
                status_msg = "SẴN SÀNG"

            if can_enter:
                if ex["question_count"] == 0:
                    ctk.CTkLabel(right_action, text="Đề chưa có câu hỏi", font=css.FONT_BADGE, text_color=css.COLOR_DANGER).pack()
                else:
                    btn_join = ctk.CTkButton(
                        right_action, text="VÀO THI NGAY ➔", width=130, height=36,
                        font=css.FONT_BODY_BOLD, fg_color=css.COLOR_SUCCESS, hover_color="#15803D",
                        command=lambda e=ex: self.start_exam_session(e)
                    )
                    btn_join.pack()
            else:
                ctk.CTkLabel(right_action, text=status_msg, font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MUTED, justify="center").pack()

    # --- HÀM XỬ LÝ CHAT ---
    def send_chat_message(self):
        text = self.in_chat.get().strip()
        if not text or not self.chat_sock:
            return
        try:
            send_msg(self.chat_sock, {
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
        is_admin = ("Admin" in sender)

        msg_box = ctk.CTkFrame(self.chat_scroll, fg_color=css.COLOR_CARD_ALT, corner_radius=8, border_width=1, border_color=css.COLOR_BORDER)
        msg_box.pack(fill="x", pady=3, padx=2)

        if is_admin:
            msg_box.configure(fg_color="#EFF6FF", border_color="#BFDBFE")
            ctk.CTkLabel(msg_box, text=f"👑 {sender} ({send_time})", font=css.FONT_BODY_BOLD, text_color=css.COLOR_ACCENT).pack(anchor="w", padx=8, pady=(4, 1))
            ctk.CTkLabel(msg_box, text=text, font=css.FONT_BODY, text_color=css.COLOR_TEXT_MAIN, wraplength=280, justify="left").pack(anchor="w", padx=8, pady=(0, 4))
        else:
            sender_color = css.COLOR_ACCENT if is_me else "#0F766E"
            header_text = f"👤 Bạn ({send_time})" if is_me else f"👤 {sender} ({send_time})"
            ctk.CTkLabel(msg_box, text=header_text, font=css.FONT_BADGE, text_color=sender_color).pack(anchor="w", padx=8, pady=(4, 1))
            ctk.CTkLabel(msg_box, text=text, font=css.FONT_BODY, text_color=css.COLOR_TEXT_MAIN, wraplength=280, justify="left").pack(anchor="w", padx=8, pady=(0, 4))

    # =========================================================================
    # 3. PHÒNG THI TRẮC NGHIỆM
    # =========================================================================
    def start_exam_session(self, exam):
        self.current_exam = exam
        try:
            send_msg(self.sock, {"action": "GET_QUESTIONS", "topic_id": exam["topic_id"]})
            res = recv_msg(self.sock)
            self.questions = res.get("questions", [])
        except Exception:
            messagebox.showerror("Lỗi", "Không thể lấy câu hỏi từ máy chủ!")
            return

        if not self.questions:
            messagebox.showwarning("Thông báo", "Bộ đề này chưa có câu hỏi nào để thi!")
            return

        self.current_q_index = 0
        self.user_answers = {}

        try:
            dur = int(exam.get("duration_minutes", 15))
        except (ValueError, TypeError):
            dur = 15
        self.time_left_seconds = dur * 60

        self.render_arena_ui()
        self.start_timer_thread()

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

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=25, pady=10)

        nav_bar = ctk.CTkFrame(body, fg_color="transparent", height=45)
        nav_bar.pack(fill="x", side="bottom", pady=(8, 0))

        self.btn_prev = ctk.CTkButton(nav_bar, text="◀ Câu trước", width=110, height=36, font=css.FONT_BODY_BOLD, fg_color="#E2E8F0", text_color=css.COLOR_TEXT_MAIN, hover_color="#CBD5E1", command=self.prev_question)
        self.btn_prev.pack(side="left")

        self.btn_next = ctk.CTkButton(nav_bar, text="Câu tiếp theo ▶", width=120, height=36, font=css.FONT_BODY_BOLD, fg_color=css.COLOR_ACCENT, hover_color="#1D4ED8", command=self.next_question)
        self.btn_next.pack(side="right")

        q_card = ctk.CTkScrollableFrame(body, **css.STYLE_CARD)
        q_card.pack(fill="both", expand=True, side="top")

        self.lbl_q_step = ctk.CTkLabel(q_card, text="", font=css.FONT_BADGE, text_color=css.COLOR_ACCENT, fg_color="#EFF6FF", corner_radius=6, padx=10, pady=3)
        self.lbl_q_step.pack(anchor="w", padx=20, pady=(15, 8))

        self.lbl_question_content = ctk.CTkLabel(q_card, text="", font=("Segoe UI", 15, "bold"), text_color=css.COLOR_TEXT_MAIN, wraplength=760, justify="left")
        self.lbl_question_content.pack(anchor="w", padx=20, pady=(5, 15))

        self.opt_buttons = {}
        for opt in ["A", "B", "C", "D"]:
            btn = ctk.CTkButton(
                q_card, text="", font=css.FONT_BODY, height=44, corner_radius=8,
                fg_color=css.COLOR_CARD_ALT, text_color=css.COLOR_TEXT_MAIN,
                border_width=1.5, border_color=css.COLOR_BORDER, hover_color="#E2E8F0",
                anchor="w", command=lambda o=opt: self.select_option(o)
            )
            btn.pack(fill="x", padx=20, pady=4)
            self.opt_buttons[opt] = btn

        self.display_current_question()

    def display_current_question(self):
        q = self.questions[self.current_q_index]
        total = len(self.questions)
        self.lbl_q_step.configure(text=f"CÂU HỎI {self.current_q_index + 1} / {total}")
        self.lbl_question_content.configure(text=q["question"])

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
    # 4. ĐỒNG HỒ ĐẾM NGƯỢC
    # =========================================================================
    def start_timer_thread(self):
        self.timer_running = True
        def countdown():
            while self.time_left_seconds > 0 and self.timer_running:
                time.sleep(1)
                self.time_left_seconds -= 1
                mins, secs = divmod(self.time_left_seconds, 60)
                time_str = f"⏱ {mins:02d}:{secs:02d}"
                self.after(0, self.update_clock_ui, time_str)

            if self.time_left_seconds <= 0 and self.timer_running:
                self.after(0, self.time_out_auto_submit)

        threading.Thread(target=countdown, daemon=True).start()

    def update_clock_ui(self, time_str):
        if hasattr(self, 'lbl_clock') and self.lbl_clock.winfo_exists():
            self.lbl_clock.configure(text=time_str)
            if self.time_left_seconds <= 60:
                self.lbl_clock.configure(text_color=css.COLOR_DANGER)

    def time_out_auto_submit(self):
        self.timer_running = False
        messagebox.showinfo("Hết giờ", "Thời gian làm bài đã kết thúc! Hệ thống sẽ tự động nộp bài.")
        self.calculate_and_show_result()

    def confirm_finish_exam(self):
        answered = len(self.user_answers)
        total = len(self.questions)
        if messagebox.askyesno("Nộp bài thi", f"Bạn đã làm {answered}/{total} câu hỏi.\nBạn có chắc chắn muốn nộp bài thi ngay không?"):
            self.timer_running = False
            self.calculate_and_show_result()

    # =========================================================================
    # 5. TỔNG KẾT VÀ NỘP BÀI QUA SOCKET
    # =========================================================================
    def calculate_and_show_result(self):
        self.clear_screen()
        correct_count = 0
        total = len(self.questions)

        for idx, q in enumerate(self.questions):
            ans = self.user_answers.get(idx, None)
            if ans == q["correct_answer"]:
                correct_count += 1

        score_10 = round((correct_count / total) * 10, 1) if total > 0 else 0

        try:
            send_msg(self.sock, {
                "action": "SUBMIT_EXAM",
                "exam_id": self.current_exam["id"],
                "student_name": self.student_name,
                "correct_count": correct_count,
                "total_questions": total,
                "score": score_10
            })
            recv_msg(self.sock)
        except Exception as e:
            print("[-] Lỗi khi gửi kết quả về Server:", e)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        card = ctk.CTkFrame(container, width=460, height=450, **css.STYLE_CARD)
        card.pack()
        card.pack_propagate(False)

        ctk.CTkLabel(card, text="🎉 KẾT QUẢ BÀI THI", font=css.FONT_TITLE, text_color=css.COLOR_TEXT_MAIN).pack(pady=(35, 5))
        ctk.CTkLabel(card, text=f"Thí sinh: {self.student_name}", font=css.FONT_BODY_BOLD, text_color=css.COLOR_ACCENT).pack(pady=(0, 20))

        score_box = ctk.CTkFrame(card, height=110, fg_color="#EFF6FF", corner_radius=12, border_width=1, border_color="#DBEAFE")
        score_box.pack(fill="x", padx=40, pady=(0, 20))
        score_box.pack_propagate(False)

        ctk.CTkLabel(score_box, text=f"{score_10} / 10", font=("Segoe UI", 32, "bold"), text_color=css.COLOR_ACCENT).pack(pady=(15, 0))
        ctk.CTkLabel(score_box, text=f"Đúng {correct_count} trên tổng số {total} câu hỏi", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack()

        btn_lobby = ctk.CTkButton(card, text="Quay về Sảnh chờ thi", width=320, **css.STYLE_PRIMARY_BTN, command=self.show_exam_lobby)
        btn_lobby.pack(pady=10)

if __name__ == "__main__":
    app = StudentExamApp()
    app.mainloop()