import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
try:
    import client.theme as css
except ModuleNotFoundError:
    import theme as css

class ExamView(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="QUẢN LÝ KỲ THI TRỰC TUYẾN", font=css.FONT_TITLE, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(self, text="Lên lịch thi, thiết lập thời gian làm bài và theo dõi kết quả của các thí sinh.", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(anchor="w", pady=(2, 10))

        # Khung Tạo Ca Thi
        box_create = ctk.CTkFrame(self, **css.STYLE_CARD)
        box_create.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(box_create, text="⏱ THIẾT LẬP CA THI MỚI", font=css.FONT_BODY_BOLD, text_color=css.COLOR_ACCENT).pack(anchor="w", padx=15, pady=(8, 4))

        row1 = ctk.CTkFrame(box_create, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=(0, 6))

        self.in_title = ctk.CTkEntry(row1, placeholder_text="Tên kỳ thi...", **css.STYLE_ENTRY)
        self.in_title.pack(side="left", fill="x", expand=True, padx=5)

        self.combo_topics = ctk.CTkComboBox(row1, width=280, height=36, state="readonly", fg_color=css.COLOR_CARD, text_color=css.COLOR_TEXT_MAIN, border_color=css.COLOR_BORDER)
        self.combo_topics.pack(side="right", padx=5)

        row2 = ctk.CTkFrame(box_create, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(0, 10))

        self.in_start_time = ctk.CTkEntry(row2, placeholder_text="Thời gian mở: YYYY-MM-DD HH:MM", **css.STYLE_ENTRY)
        self.in_start_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.in_start_time.pack(side="left", fill="x", expand=True, padx=5)

        self.in_duration = ctk.CTkEntry(row2, placeholder_text="Thời lượng (phút)...", width=140, **css.STYLE_ENTRY)
        self.in_duration.insert(0, "15")
        self.in_duration.pack(side="left", padx=5)

        ctk.CTkButton(row2, text="➕ Lưu & Phát Hành", width=160, **css.STYLE_SUCCESS_BTN, command=self.action_add_exam).pack(side="right", padx=5)

        # Danh Sách Ca Thi
        header_list = ctk.CTkFrame(self, fg_color="transparent")
        header_list.pack(fill="x", pady=(5, 4))

        ctk.CTkLabel(header_list, text="📋 DANH SÁCH CÁC KỲ THI ĐÃ TẠO", font=css.FONT_SECTION, text_color=css.COLOR_TEXT_MAIN).pack(side="left")
        ctk.CTkButton(header_list, text="🔄 Làm mới", width=90, height=30, font=css.FONT_BADGE, fg_color="#EFF6FF", text_color=css.COLOR_ACCENT, hover_color="#DBEAFE", command=self.refresh_all).pack(side="right")

        self.exam_scroll = ctk.CTkScrollableFrame(self, **css.STYLE_CARD)
        self.exam_scroll.pack(fill="both", expand=True)

        self.refresh_all()

    def refresh_all(self):
        self.load_topics_dropdown()
        self.load_exams_cards()

    def load_topics_dropdown(self):
        topics = self.db.get_topics()
        if not topics:
            self.combo_topics.configure(values=["Chưa có đề tài nào"])
            self.combo_topics.set("Chưa có đề tài nào")
            return

        options = [f"{t['id']} - {t['name']} ({t.get('question_count', 0)} câu)" for t in topics]
        self.combo_topics.configure(values=options)
        self.combo_topics.set(options[0])

    def action_add_exam(self):
        title = self.in_title.get().strip()
        topic_val = self.combo_topics.get().strip()
        duration_str = self.in_duration.get().strip()
        start_time = self.in_start_time.get().strip()

        if not title:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập tên kỳ thi!")
            return

        if not topic_val or topic_val == "Chưa có đề tài nào":
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bộ đề thi!")
            return

        # Tách chính xác topic_id đứng trước dấu gạch ngang đầu tiên
        try:
            topic_id = int(topic_val.split("-")[0].strip())
        except (ValueError, IndexError):
            messagebox.showerror("Lỗi", "Không xác định được ID đề tài!")
            return

        try:
            duration = int(duration_str)
        except ValueError:
            messagebox.showwarning("Cảnh báo", "Thời lượng thi phải là số nguyên (phút)!")
            return

        # Lưu vào Database
        self.db.add_exam(topic_id, title, duration, start_time)
        messagebox.showinfo("Thành công", f"Đã lên lịch kỳ thi: {title}")

        # Xóa trắng ô nhập tên
        self.in_title.delete(0, "end")

        # Nạp lại danh sách hiển thị thẻ kỳ thi ngay lập tức
        self.load_exams_cards()

    def load_exams_cards(self):
        for w in self.exam_scroll.winfo_children():
            w.destroy()

        exams = self.db.get_exams()
        if not exams:
            ctk.CTkLabel(self.exam_scroll, text="Chưa có ca thi nào được tạo. Hãy thiết lập ở khung trên!", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(pady=40)
            return

        for ex in exams:
            card = ctk.CTkFrame(self.exam_scroll, fg_color=css.COLOR_CARD_ALT, corner_radius=10, border_width=1, border_color=css.COLOR_BORDER)
            card.pack(fill="x", pady=5, padx=5)

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", padx=15, pady=10)
            ctk.CTkLabel(info, text=f"⏱ {ex['title']}", font=css.FONT_SECTION, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w")
            ctk.CTkLabel(info, text=f"Bộ đề: {ex['topic_name']}  •  Thời lượng: {ex['duration_minutes']} phút  •  Đã thi: {ex.get('participant_count', 0)} thí sinh", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(anchor="w")

            ctk.CTkLabel(card, text=f"📅 Bắt đầu: {ex['start_time']}", font=css.FONT_BADGE, text_color=css.COLOR_ACCENT).pack(side="left", padx=15)

            btn_box = ctk.CTkFrame(card, fg_color="transparent")
            btn_box.pack(side="right", padx=15)

            # Nút Xem danh sách kết quả bài thi
            btn_results = ctk.CTkButton(
                btn_box, text="📊 Xem kết quả", width=110, height=30,
                font=css.FONT_BADGE, fg_color="#EFF6FF", text_color=css.COLOR_ACCENT, hover_color="#DBEAFE",
                command=lambda e=ex: self.open_results_window(e)
            )
            btn_results.pack(side="left", padx=5)

            # Nút Xóa ca thi
            btn_del = ctk.CTkButton(btn_box, text="Xóa", width=55, **css.STYLE_DANGER_BTN, command=lambda eid=ex["id"]: self.delete_exam_item(eid))
            btn_del.pack(side="left", padx=5)

    def delete_exam_item(self, exam_id):
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn xóa kỳ thi này? Dữ liệu kết quả thi liên quan cũng sẽ bị xóa."):
            self.db.delete_exam(exam_id)
            self.load_exams_cards()

    # --- POPUP XEM BẢNG ĐIỂM CHI TIẾT ---
    def open_results_window(self, exam):
        popup = ctk.CTkToplevel(self)
        popup.title(f"KẾT QUẢ THI: {exam['title']}")
        popup.geometry("680x520")
        popup.minsize(600, 400)
        popup.configure(fg_color=css.COLOR_BG)
        popup.grab_set()

        top = ctk.CTkFrame(popup, fg_color=css.COLOR_CARD, corner_radius=0, border_width=1, border_color=css.COLOR_BORDER)
        top.pack(fill="x", padx=0, pady=(0, 15))
        ctk.CTkLabel(top, text=f"BẢNG ĐIỂM KỲ THI: {exam['title']}", font=css.FONT_SECTION, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w", padx=20, pady=(15, 2))
        ctk.CTkLabel(top, text=f"Bộ đề: {exam['topic_name']}  •  Thời gian mở: {exam['start_time']}", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(anchor="w", padx=20, pady=(0, 15))

        scroll = ctk.CTkScrollableFrame(popup, **css.STYLE_CARD)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        results = self.db.get_exam_results(exam["id"])
        if not results:
            ctk.CTkLabel(scroll, text="Chưa có thí sinh nào hoàn thành bài thi này.\nHãy đăng nhập tài khoản thí sinh để làm bài!", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(pady=60)
            return

        # Header bảng dữ liệu
        h_frame = ctk.CTkFrame(scroll, fg_color="#F1F5F9", corner_radius=6)
        h_frame.pack(fill="x", pady=(0, 6), padx=4)
        ctk.CTkLabel(h_frame, text="HỌ VÀ TÊN", width=180, anchor="w", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(h_frame, text="SỐ CÂU ĐÚNG", width=120, anchor="center", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(side="left", padx=5)
        ctk.CTkLabel(h_frame, text="ĐIỂM SỐ", width=90, anchor="center", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(side="left", padx=5)
        ctk.CTkLabel(h_frame, text="THỜI GIAN NỘP", width=150, anchor="center", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(side="left", padx=5)

        for r in results:
            r_frame = ctk.CTkFrame(scroll, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color=css.COLOR_BORDER)
            r_frame.pack(fill="x", pady=3, padx=4)

            ctk.CTkLabel(r_frame, text=f"👤 {r['student_name']}", width=180, anchor="w", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(side="left", padx=10, pady=10)
            ctk.CTkLabel(r_frame, text=f"{r['correct_count']} / {r['total_questions']} câu", width=120, anchor="center", font=css.FONT_BODY, text_color=css.COLOR_TEXT_MUTED).pack(side="left", padx=5)

            score = r['score']
            badge_color = css.COLOR_SUCCESS if score >= 8 else (css.COLOR_WARNING if score >= 5 else css.COLOR_DANGER)
            badge_bg = "#DCFCE7" if score >= 8 else ("#FEF3C7" if score >= 5 else "#FEE2E2")
            badge = ctk.CTkLabel(r_frame, text=f"{score} đ", width=65, height=24, font=css.FONT_BADGE, text_color=badge_color, fg_color=badge_bg, corner_radius=4)
            badge.pack(side="left", padx=18)

            c_time = r['completed_at']
            if len(c_time) >= 16:
                c_time = c_time[:16]
            ctk.CTkLabel(r_frame, text=c_time, width=150, anchor="center", font=css.FONT_BODY, text_color=css.COLOR_TEXT_MUTED).pack(side="left", padx=5)