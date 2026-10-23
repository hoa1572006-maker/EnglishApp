import customtkinter as ctk
from tkinter import messagebox
try:
    import client.theme as css
except ModuleNotFoundError:
    import theme as css

class TopicView(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.editing_q_id = None
        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="QUẢN LÝ ĐỀ TÀI & CÂU HỎI", font=css.FONT_TITLE, text_color=css.COLOR_TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(self, text="Tạo đề tài mới, soạn câu hỏi và quản lý danh sách chi tiết (Xem / Sửa / Xóa)", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(anchor="w", pady=(2, 10))

        # Khung 1: Tạo đề tài mới
        box_create_topic = ctk.CTkFrame(self, **css.STYLE_CARD)
        box_create_topic.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(box_create_topic, text="➕ TẠO ĐỀ TÀI MỚI", font=css.FONT_BODY_BOLD, text_color=css.COLOR_ACCENT).pack(anchor="w", padx=15, pady=(8, 4))

        row_t = ctk.CTkFrame(box_create_topic, fg_color="transparent")
        row_t.pack(fill="x", padx=10, pady=(0, 8))

        self.in_t_name = ctk.CTkEntry(row_t, placeholder_text="Tên đề tài ...", **css.STYLE_ENTRY)
        self.in_t_name.pack(side="left", fill="x", expand=True, padx=5)

        self.in_t_desc = ctk.CTkEntry(row_t, placeholder_text="Mô tả tóm tắt...", **css.STYLE_ENTRY)
        self.in_t_desc.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkButton(row_t, text="Lưu Đề Tài", width=120, **css.STYLE_SUCCESS_BTN, command=self.action_add_topic).pack(side="right", padx=5)

        # Khung 2: Form soạn / sửa câu hỏi
        self.box_questions = ctk.CTkFrame(self, **css.STYLE_CARD)
        self.box_questions.pack(fill="x", pady=(0, 10))

        header_q = ctk.CTkFrame(self.box_questions, fg_color="transparent")
        header_q.pack(fill="x", padx=15, pady=(8, 4))

        self.lbl_form_mode = ctk.CTkLabel(header_q, text="📝 SOẠN CÂU HỎI MỚI", font=css.FONT_BODY_BOLD, text_color=css.COLOR_WARNING)
        self.lbl_form_mode.pack(side="left")

        self.btn_cancel_edit = ctk.CTkButton(header_q, text="✖ Hủy chế độ sửa", width=110, height=26, fg_color="#E2E8F0", text_color=css.COLOR_TEXT_MAIN, hover_color="#CBD5E1", font=css.FONT_BADGE, command=self.reset_question_form)

        sel_row = ctk.CTkFrame(self.box_questions, fg_color="transparent")
        sel_row.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(sel_row, text="Đang chọn đề tài:", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(side="left", padx=(0, 10))
        
        self.combo_active_topic = ctk.CTkComboBox(sel_row, width=320, height=36, state="readonly", fg_color=css.COLOR_CARD, text_color=css.COLOR_TEXT_MAIN, border_color=css.COLOR_BORDER, command=self.on_topic_selected)
        self.combo_active_topic.pack(side="left")

        self.lbl_q_status = ctk.CTkLabel(sel_row, text="Đã có 0 câu hỏi", font=css.FONT_BADGE, text_color=css.COLOR_ACCENT)
        self.lbl_q_status.pack(side="right")

        self.in_q_title = ctk.CTkEntry(self.box_questions, placeholder_text="Nhập nội dung câu hỏi tiếng Anh...", **css.STYLE_ENTRY)
        self.in_q_title.pack(fill="x", padx=15, pady=(6, 4))

        grid_opts = ctk.CTkFrame(self.box_questions, fg_color="transparent")
        grid_opts.pack(fill="x", padx=10, pady=2)
        self.in_opt_a = ctk.CTkEntry(grid_opts, placeholder_text="Đáp án A", **css.STYLE_ENTRY)
        self.in_opt_a.pack(side="left", fill="x", expand=True, padx=5)
        self.in_opt_b = ctk.CTkEntry(grid_opts, placeholder_text="Đáp án B", **css.STYLE_ENTRY)
        self.in_opt_b.pack(side="left", fill="x", expand=True, padx=5)

        grid_opts2 = ctk.CTkFrame(self.box_questions, fg_color="transparent")
        grid_opts2.pack(fill="x", padx=10, pady=4)
        self.in_opt_c = ctk.CTkEntry(grid_opts2, placeholder_text="Đáp án C", **css.STYLE_ENTRY)
        self.in_opt_c.pack(side="left", fill="x", expand=True, padx=5)
        self.in_opt_d = ctk.CTkEntry(grid_opts2, placeholder_text="Đáp án D", **css.STYLE_ENTRY)
        self.in_opt_d.pack(side="left", fill="x", expand=True, padx=5)

        action_row = ctk.CTkFrame(self.box_questions, fg_color="transparent")
        action_row.pack(fill="x", padx=15, pady=(4, 10))

        ctk.CTkLabel(action_row, text="Đáp án đúng:", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(side="left", padx=(0, 10))
        self.combo_correct = ctk.CTkComboBox(action_row, values=["A", "B", "C", "D"], width=90, height=36, state="readonly", fg_color=css.COLOR_CARD, text_color=css.COLOR_TEXT_MAIN, border_color=css.COLOR_BORDER)
        self.combo_correct.set("A")
        self.combo_correct.pack(side="left")

        self.btn_save_q = ctk.CTkButton(action_row, text="➕ Lưu Câu Hỏi Vào Đề", width=180, **css.STYLE_PRIMARY_BTN, command=self.action_save_question)
        self.btn_save_q.pack(side="right")

        # Khung 3: Danh sách câu hỏi chi tiết
        detail_header = ctk.CTkFrame(self, fg_color="transparent")
        detail_header.pack(fill="x", pady=(5, 3))
        ctk.CTkLabel(detail_header, text="📋 CHI TIẾT CÂU HỎI TRONG ĐỀ TÀI", font=css.FONT_SECTION, text_color=css.COLOR_TEXT_MAIN).pack(side="left")

        self.questions_scroll = ctk.CTkScrollableFrame(self, **css.STYLE_CARD)
        self.questions_scroll.pack(fill="both", expand=True)

        self.refresh_topics_ui()

    def get_current_topic_id(self):
        val = self.combo_active_topic.get().strip()
        if not val or val == "Chưa có đề tài nào":
            return None
        try:
            return int(val.split("-")[0].strip())
        except (ValueError, IndexError):
            return None

    def refresh_topics_ui(self, keep_id=None):
        topics = self.db.get_topics()
        if not topics:
            self.combo_active_topic.configure(values=["Chưa có đề tài nào"])
            self.combo_active_topic.set("Chưa có đề tài nào")
            self.lbl_q_status.configure(text="Đã có 0 câu hỏi")
            self.load_questions_list([])
            return

        options = [f"{t['id']} - {t['name']}" for t in topics]
        self.combo_active_topic.configure(values=options)

        target_opt = options[0]
        if keep_id:
            for opt in options:
                if opt.startswith(f"{keep_id} -"):
                    target_opt = opt
                    break

        self.combo_active_topic.set(target_opt)
        self.on_topic_selected(target_opt)

    def on_topic_selected(self, selected_text=None):
        topic_id = self.get_current_topic_id()
        if topic_id is None:
            self.lbl_q_status.configure(text="Đã có 0 câu hỏi")
            self.load_questions_list([])
            return

        qs = self.db.get_questions_by_topic(topic_id)
        count = len(qs) if qs else 0
        self.lbl_q_status.configure(text=f"Đã có {count} câu hỏi")
        self.load_questions_list(qs)

    def load_questions_list(self, questions):
        for w in self.questions_scroll.winfo_children():
            w.destroy()

        if not questions:
            ctk.CTkLabel(self.questions_scroll, text="Chưa có câu hỏi nào trong đề tài này. Hãy nhập ở form phía trên!", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(pady=30)
            return

        for idx, q in enumerate(questions, start=1):
            card = ctk.CTkFrame(self.questions_scroll, fg_color=css.COLOR_CARD_ALT, corner_radius=10, border_width=1, border_color=css.COLOR_BORDER)
            card.pack(fill="x", pady=4, padx=5)

            left_info = ctk.CTkFrame(card, fg_color="transparent")
            left_info.pack(side="left", fill="both", expand=True, padx=14, pady=8)

            q_title_txt = f"Câu {idx}: {q['question']}"
            ctk.CTkLabel(left_info, text=q_title_txt, font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN, wraplength=550, justify="left").pack(anchor="w")

            opts_preview = f"A. {q['option_a']}  |  B. {q['option_b']}  |  C. {q['option_c']}  |  D. {q['option_d']}"
            ctk.CTkLabel(left_info, text=opts_preview, font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED, wraplength=550, justify="left").pack(anchor="w", pady=(2, 0))

            right_actions = ctk.CTkFrame(card, fg_color="transparent")
            right_actions.pack(side="right", padx=14, pady=8)

            ans_badge = ctk.CTkLabel(right_actions, text=f"Đáp án: {q['correct_answer']}", font=css.FONT_BADGE, text_color=css.COLOR_ACCENT, fg_color="#DBEAFE", corner_radius=6, width=75, height=24)
            ans_badge.pack(side="left", padx=6)

            btn_edit = ctk.CTkButton(right_actions, text="Sửa", width=55, height=28, font=css.FONT_BADGE, fg_color="#E0E7FF", text_color="#3730A3", hover_color="#C7D2FE", command=lambda item=q: self.start_edit_question(item))
            btn_edit.pack(side="left", padx=4)

            btn_del = ctk.CTkButton(right_actions, text="Xóa", width=55, **css.STYLE_DANGER_BTN, command=lambda qid=q["id"]: self.action_delete_question(qid))
            btn_del.pack(side="left", padx=4)

    def start_edit_question(self, q):
        self.editing_q_id = q["id"]
        self.lbl_form_mode.configure(text=f"✏️ ĐANG CHỈNH SỬA CÂU HỎI (ID: {q['id']})", text_color=css.COLOR_ACCENT)
        self.btn_cancel_edit.pack(side="right", padx=10)
        self.btn_save_q.configure(text="💾 Cập Nhật Câu Hỏi", fg_color=css.COLOR_SUCCESS, hover_color="#15803D")

        self.in_q_title.delete(0, "end")
        self.in_q_title.insert(0, q["question"])

        self.in_opt_a.delete(0, "end")
        self.in_opt_a.insert(0, q["option_a"])

        self.in_opt_b.delete(0, "end")
        self.in_opt_b.insert(0, q["option_b"])

        self.in_opt_c.delete(0, "end")
        self.in_opt_c.insert(0, q["option_c"])

        self.in_opt_d.delete(0, "end")
        self.in_opt_d.insert(0, q["option_d"])

        self.combo_correct.set(q["correct_answer"])

    def reset_question_form(self):
        self.editing_q_id = None
        self.lbl_form_mode.configure(text="📝 BƯỚC 2: SOẠN CÂU HỎI MỚI", text_color=css.COLOR_WARNING)
        self.btn_cancel_edit.pack_forget()
        self.btn_save_q.configure(text="➕ Lưu Câu Hỏi Vào Đề", fg_color=css.COLOR_ACCENT, hover_color="#1D4ED8")

        self.in_q_title.delete(0, "end")
        self.in_opt_a.delete(0, "end")
        self.in_opt_b.delete(0, "end")
        self.in_opt_c.delete(0, "end")
        self.in_opt_d.delete(0, "end")
        self.combo_correct.set("A")

    def action_save_question(self):
        topic_id = self.get_current_topic_id()
        if topic_id is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn hoặc tạo đề tài trước!")
            return

        q = self.in_q_title.get().strip()
        a = self.in_opt_a.get().strip()
        b = self.in_opt_b.get().strip()
        c = self.in_opt_c.get().strip()
        d = self.in_opt_d.get().strip()
        correct = self.combo_correct.get()

        if not q or not a or not b or not c or not d:
            messagebox.showwarning("Cảnh báo", "Vui lòng điền đủ câu hỏi và 4 đáp án A-B-C-D!")
            return

        if self.editing_q_id is None:
            self.db.add_question(topic_id, q, a, b, c, d, correct)
            messagebox.showinfo("Thành công", "Đã thêm câu hỏi vào đề tài!")
        else:
            self.db.update_question(self.editing_q_id, q, a, b, c, d, correct)
            messagebox.showinfo("Thành công", "Đã cập nhật câu hỏi thành công!")

        self.reset_question_form()
        self.on_topic_selected()

    def action_delete_question(self, qid):
        if messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa câu hỏi này khỏi đề tài?"):
            self.db.delete_question(qid)
            if self.editing_q_id == qid:
                self.reset_question_form()
            self.on_topic_selected()

    def action_add_topic(self):
        name = self.in_t_name.get().strip()
        desc = self.in_t_desc.get().strip()
        if not name:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập tên đề tài!")
            return
        new_id = self.db.add_topic(name, desc)
        messagebox.showinfo("Thành công", f"Đã tạo đề tài mới: {name}")
        self.in_t_name.delete(0, "end")
        self.in_t_desc.delete(0, "end")
        self.refresh_topics_ui(keep_id=new_id)