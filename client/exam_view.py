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
        # Tiêu đề trang
        ctk.CTkLabel(self, text="QUẢN LÝ KỲ THI TRỰC TUYẾN", font=css.FONT_TITLE, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(self, text="Lên lịch thi.", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(anchor="w", pady=(2, 15))

        # --- KHUNG TẠO KỲ THI MỚI ---
        form = ctk.CTkFrame(self, **css.STYLE_CARD)
        form.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(form, text="⏱ THIẾT LẬP CA THI MỚI", font=css.FONT_BODY_BOLD, text_color=css.COLOR_ACCENT).pack(anchor="w", padx=15, pady=(10, 5))

        # Dòng 1: Tên kỳ thi & Chọn Bộ đề
        r1 = ctk.CTkFrame(form, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=4)
        self.in_exam_title = ctk.CTkEntry(r1, placeholder_text="Tên kỳ thi...", **css.STYLE_ENTRY)
        self.in_exam_title.pack(side="left", fill="x", expand=True, padx=5)

        topics = self.db.get_topics()
        t_opts = [f"{t['id']} - {t['name']} ({t['question_count']} câu)" for t in topics] if topics else ["Chưa có đề tài nào"]
        self.combo_exam_topic = ctk.CTkComboBox(r1, values=t_opts, height=38, width=320, state="readonly", fg_color=css.COLOR_CARD, text_color=css.COLOR_TEXT_MAIN, border_color=css.COLOR_BORDER)
        self.combo_exam_topic.pack(side="left", padx=5)

        # Dòng 2: Ngày giờ mở đề, Thời lượng & Nút lưu
        r2 = ctk.CTkFrame(form, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=(0, 10))

        self.in_exam_time = ctk.CTkEntry(r2, placeholder_text="Ngày giờ mở đề (VD: 2026-09-28 14:00)...", **css.STYLE_ENTRY)
        self.in_exam_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.in_exam_time.pack(side="left", fill="x", expand=True, padx=5)

        self.in_exam_dur = ctk.CTkEntry(r2, placeholder_text="Thời lượng phút...", width=140, **css.STYLE_ENTRY)
        self.in_exam_dur.insert(0, "15")
        self.in_exam_dur.pack(side="left", padx=5)

        ctk.CTkButton(r2, text="➕ Lưu & Phát Hành", width=150, **css.STYLE_SUCCESS_BTN, command=self.action_add_exam).pack(side="right", padx=5)

        # --- KHUNG DANH SÁCH CÁC KỲ THI ĐÃ TẠO ---
        self.exam_scroll = ctk.CTkScrollableFrame(self, **css.STYLE_CARD)
        self.exam_scroll.pack(fill="both", expand=True)
        self.load_exams_cards()

    def action_add_exam(self):
        title = self.in_exam_title.get().strip()
        t_sel = self.combo_exam_topic.get()
        start_t = self.in_exam_time.get().strip()
        dur_str = self.in_exam_dur.get().strip()

        if not title or " - " not in t_sel or not start_t:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập tên kỳ thi và chọn một đề tài hợp lệ!")
            return

        try:
            dur = int(dur_str)
        except ValueError:
            messagebox.showwarning("Cảnh báo", "Thời lượng thi phải là số nguyên!")
            return

        topic_id = int(t_sel.split(" - ")[0])
        self.db.add_exam(title, topic_id, start_t, dur)
        messagebox.showinfo("Thành công", f"Đã lên lịch kỳ thi: {title}")
        self.in_exam_title.delete(0, "end")
        self.load_exams_cards()

    def load_exams_cards(self):
        for w in self.exam_scroll.winfo_children():
            w.destroy()

        exams = self.db.get_exams()
        if not exams:
            ctk.CTkLabel(self.exam_scroll, text="Chưa có kỳ thi nào. Hãy tạo kỳ thi mới ở phía trên!", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(pady=40)
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
        ctk.CTkLabel(h_frame, text="THỜI GIAN NỘP", width=140, anchor="e", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(side="right", padx=10)

        # Danh sách thí sinh & điểm
        for r in results:
            row = ctk.CTkFrame(scroll, fg_color=css.COLOR_CARD_ALT, corner_radius=6, border_width=1, border_color=css.COLOR_BORDER)
            row.pack(fill="x", pady=3, padx=4)

            ctk.CTkLabel(row, text=f"👤 {r['student_name']}", width=180, anchor="w", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(side="left", padx=10, pady=10)
            ctk.CTkLabel(row, text=f"{r['correct_count']} / {r['total_questions']} câu", width=120, anchor="center", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(side="left", padx=5)
            
            score_color = "#15803D" if r['score'] >= 5.0 else "#DC2626"
            score_bg = "#DCFCE7" if r['score'] >= 5.0 else "#FEE2E2"
            lbl_score = ctk.CTkLabel(row, text=f"{r['score']} đ", width=70, height=24, font=css.FONT_BADGE, text_color=score_color, fg_color=score_bg, corner_radius=6)
            lbl_score.pack(side="left", padx=15)

            ctk.CTkLabel(row, text=str(r['completed_at'])[:16], width=140, anchor="e", font=css.FONT_BADGE, text_color=css.COLOR_TEXT_MUTED).pack(side="right", padx=10)