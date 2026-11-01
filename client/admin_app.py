import customtkinter as ctk
import threading
import socket
import sys
import os

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from server.database import Database
from shared.protocol import send_msg, recv_msg

try:
    import client.theme as css
    from client.topic_view import TopicView
    from client.exam_view import ExamView
    from client.chat_view import AdminChatView
except ModuleNotFoundError:
    import theme as css
    from topic_view import TopicView
    from exam_view import ExamView
    from chat_view import AdminChatView

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class ProctorView(ctk.CTkFrame):
    """Giao diện giám sát phòng thi thời gian thực có lọc theo kỳ thi"""
    def __init__(self, parent, db, server_ip="192.168.1.26", server_port=8888):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = None
        self.is_running = True
        self.raw_students_data = []

        self.setup_ui()
        self.connect_proctor_socket()

    def setup_ui(self):
        # 1. Hàng tiêu đề & Trạng thái kết nối
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(header, text="GIÁM SÁT PHÒNG THI THỜI GIAN THỰC (LIVE PROCTORING)", font=css.FONT_TITLE, text_color=css.COLOR_TEXT_MAIN).pack(side="left")
        
        self.lbl_conn_status = ctk.CTkLabel(header, text="Đang kết nối...", font=css.FONT_BADGE, text_color=css.COLOR_WARNING)
        self.lbl_conn_status.pack(side="right", padx=10)

        ctk.CTkButton(header, text="🔄 Làm mới", width=90, height=32, font=css.FONT_BADGE, fg_color="#EFF6FF", text_color=css.COLOR_ACCENT, hover_color="#DBEAFE", command=self.refresh_all).pack(side="right")

        # 2. Thanh bộ lọc kỳ thi
        filter_bar = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color=css.COLOR_BORDER, height=48)
        filter_bar.pack(fill="x", pady=(0, 10))
        filter_bar.pack_propagate(False)

        ctk.CTkLabel(filter_bar, text="🎯 Chọn kỳ thi giám sát:", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN).pack(side="left", padx=(15, 10))

        exams = self.db.get_exams()
        self.exam_options = ["Tất cả kỳ thi"] + [ex["title"] for ex in exams]

        self.combo_filter_exam = ctk.CTkComboBox(
            filter_bar, 
            values=self.exam_options, 
            width=280, 
            height=32, 
            state="readonly",
            command=self.on_filter_changed
        )
        self.combo_filter_exam.set("Tất cả kỳ thi")
        self.combo_filter_exam.pack(side="left", padx=5)

        self.lbl_filter_hint = ctk.CTkLabel(filter_bar, text="Đang hiển thị toàn bộ thí sinh", font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED)
        self.lbl_filter_hint.pack(side="left", padx=15)

        # 3. Thẻ thống kê số liệu
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 10))

        self.card_online = self.create_stat_card(stats_frame, "THÍ SINH THAM GIA", "0", css.COLOR_ACCENT)
        self.card_online.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.card_examining = self.create_stat_card(stats_frame, "ĐANG LÀM BÀI", "0", css.COLOR_SUCCESS)
        self.card_examining.pack(side="left", fill="x", expand=True, padx=5)

        self.card_violations = self.create_stat_card(stats_frame, "TỔNG VI PHẠM (ALT+TAB)", "0", css.COLOR_DANGER)
        self.card_violations.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # 4. Header bảng danh sách
        table_header = ctk.CTkFrame(self, height=40, fg_color="#E2E8F0", corner_radius=8)
        table_header.pack(fill="x", pady=(5, 2))
        table_header.pack_propagate(False)

        ctk.CTkLabel(table_header, text="Thí sinh", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN, width=150, anchor="w").pack(side="left", padx=15)
        ctk.CTkLabel(table_header, text="Kỳ thi", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN, width=200, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(table_header, text="Trạng thái", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN, width=140, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(table_header, text="Thời gian còn lại", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN, width=130, anchor="center").pack(side="left", padx=10)
        ctk.CTkLabel(table_header, text="Vi phạm rời màn hình", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN, width=150, anchor="center").pack(side="left", padx=10)

        # 5. Vùng cuộn danh sách thí sinh
        self.table_scroll = ctk.CTkScrollableFrame(self, **css.STYLE_CARD)
        self.table_scroll.pack(fill="both", expand=True)

    def create_stat_card(self, parent, title, val, color):
        card = ctk.CTkFrame(parent, height=65, **css.STYLE_CARD)
        card.pack_propagate(False)
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 10, "bold"), text_color=css.COLOR_TEXT_MUTED).pack(anchor="w", padx=12, pady=(6, 0))
        lbl_v = ctk.CTkLabel(card, text=val, font=("Segoe UI", 18, "bold"), text_color=color)
        lbl_v.pack(anchor="w", padx=12)
        card.val_label = lbl_v
        return card

    def refresh_all(self):
        exams = self.db.get_exams()
        current_sel = self.combo_filter_exam.get()
        self.exam_options = ["Tất cả kỳ thi"] + [ex["title"] for ex in exams]
        self.combo_filter_exam.configure(values=self.exam_options)
        if current_sel in self.exam_options:
            self.combo_filter_exam.set(current_sel)
        else:
            self.combo_filter_exam.set("Tất cả kỳ thi")

        self.request_proctor_data()

    def on_filter_changed(self, selected_exam):
        if selected_exam == "Tất cả kỳ thi":
            self.lbl_filter_hint.configure(text="Đang hiển thị toàn bộ thí sinh")
        else:
            self.lbl_filter_hint.configure(text=f"Đang lọc phòng thi: {selected_exam}")
        self.apply_filter_and_render()

    def connect_proctor_socket(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((self.server_ip, self.server_port))
            self.sock.settimeout(None)

            send_msg(self.sock, {"action": "REGISTER_USER", "student_name": "Admin_Supervisor"})
            self.lbl_conn_status.configure(text="● Kết nối thời gian thực OK", text_color=css.COLOR_SUCCESS)

            threading.Thread(target=self.listen_loop, daemon=True).start()
            self.request_proctor_data()
        except Exception as e:
            self.lbl_conn_status.configure(text=f"Mất kết nối Server ({e})", text_color=css.COLOR_DANGER)

    def request_proctor_data(self):
        if self.sock:
            try:
                send_msg(self.sock, {"action": "GET_PROCTOR_DATA"})
            except Exception:
                pass

    def listen_loop(self):
        while self.is_running and self.sock:
            try:
                msg = recv_msg(self.sock)
                if not msg:
                    break
                if msg.get("type") == "PROCTOR_BROADCAST":
                    self.raw_students_data = msg.get("students", [])
                    self.after(0, self.apply_filter_and_render)
            except Exception:
                break

    def apply_filter_and_render(self):
        selected_exam = self.combo_filter_exam.get().strip()
        
        # 1. Lấy thí sinh đang kết nối trực tuyến (Socket)
        if selected_exam == "Tất cả kỳ thi":
            filtered = [dict(s) for s in self.raw_students_data]
        else:
            filtered = [
                dict(s) for s in self.raw_students_data 
                if s.get("exam_title", "").strip().lower() == selected_exam.lower()
            ]

        # 2. Bổ sung các thí sinh đã nộp bài được lưu trong CSDL
        existing_names = {s["name"].strip().lower() for s in filtered}
        exams = self.db.get_exams()
        target_exams = [e for e in exams if selected_exam == "Tất cả kỳ thi" or e["title"].strip().lower() == selected_exam.lower()]

        for ex in target_exams:
            res_list = self.db.get_exam_results(ex["id"])
            for r in res_list:
                s_name = r["student_name"].strip()
                if s_name.lower() not in existing_names:
                    # Lấy số lần vi phạm đã lưu từ CSDL thay vì gán về 0
                    stored_viol = r.get("violations", 0)
                    if stored_viol is None:
                        stored_viol = 0

                    filtered.append({
                        "name": s_name,
                        "exam_title": ex["title"],
                        "status": f"ĐÃ NỘP ({r['score']}/10)",
                        "time_left": 0,
                        "violations": stored_viol,
                        "last_update": r.get("completed_at", "")
                    })
                    existing_names.add(s_name.lower())

        self.render_student_rows(filtered)

    def render_student_rows(self, students):
        for w in self.table_scroll.winfo_children():
            w.destroy()

        total_online = len(students)
        examining_count = sum(1 for s in students if "LÀM BÀI" in s.get("status", ""))
        total_viol = sum(s.get("violations", 0) for s in students)

        self.card_online.val_label.configure(text=str(total_online))
        self.card_examining.val_label.configure(text=str(examining_count))
        self.card_violations.val_label.configure(text=str(total_viol))

        if not students:
            selected_exam = self.combo_filter_exam.get().strip()
            msg = f"Chưa có thí sinh nào tham gia kỳ thi '{selected_exam}'." if selected_exam != "Tất cả kỳ thi" else "Hiện chưa có thí sinh nào vào phòng thi."
            ctk.CTkLabel(self.table_scroll, text=msg, font=css.FONT_SUBTITLE, text_color=css.COLOR_TEXT_MUTED).pack(pady=40)
            return

        for s in students:
            row = ctk.CTkFrame(self.table_scroll, height=44, fg_color=css.COLOR_CARD_ALT, corner_radius=6, border_width=1, border_color=css.COLOR_BORDER)
            row.pack(fill="x", pady=3, padx=2)
            row.pack_propagate(False)

            # 1. Tên thí sinh
            ctk.CTkLabel(row, text=f"👤 {s['name']}", font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN, width=150, anchor="w").pack(side="left", padx=15)

            # 2. Đề thi
            ctk.CTkLabel(row, text=s.get("exam_title", "Chưa thi"), font=css.FONT_BODY, text_color=css.COLOR_TEXT_MUTED, width=200, anchor="w").pack(side="left", padx=10)

            # 3. Trạng thái làm bài
            status = s.get("status", "ONLINE")
            st_color = css.COLOR_SUCCESS if "LÀM BÀI" in status else (css.COLOR_ACCENT if "ĐÃ NỘP" in status else css.COLOR_DANGER)
            st_bg = "#DCFCE7" if "LÀM BÀI" in status else ("#EFF6FF" if "ĐÃ NỘP" in status else "#FEE2E2")
            badge = ctk.CTkLabel(row, text=status, font=css.FONT_BADGE, text_color=st_color, fg_color=st_bg, corner_radius=6, width=140, height=26)
            badge.pack(side="left", padx=10)

            # 4. Thời gian còn lại
            sec = s.get("time_left", 0)
            mins, s_rem = divmod(sec, 60)
            time_txt = f"{mins:02d}:{s_rem:02d}" if sec > 0 else "--:--"
            ctk.CTkLabel(row, text=time_txt, font=css.FONT_BODY_BOLD, text_color=css.COLOR_TEXT_MAIN, width=130, anchor="center").pack(side="left", padx=10)

            # 5. Vi phạm Alt+Tab
            viol = s.get("violations", 0)
            viol_txt = f"⚠ {viol} lần rời tab" if viol > 0 else "0 (An toàn)"
            viol_color = css.COLOR_DANGER if viol > 0 else "#15803D"
            viol_bg = "#FEE2E2" if viol > 0 else "#F0FDF4"
            viol_badge = ctk.CTkLabel(row, text=viol_txt, font=css.FONT_BADGE, text_color=viol_color, fg_color=viol_bg, corner_radius=6, width=140, height=26)
            viol_badge.pack(side="left", padx=10)

    def destroy(self):
        self.is_running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        super().destroy()

class AdminMasterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("QUẢN TRỊ ĐÀO TẠO TIẾNG ANH • ADMIN WORKSPACE")
        self.geometry("1140x740")
        self.minsize(1050, 680)
        self.configure(fg_color=css.COLOR_BG)

        self.db = Database()
        self.current_chat_view = None
        self.setup_ui()

    def setup_ui(self):
        self.sidebar = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=css.COLOR_SIDEBAR, border_width=1, border_color=css.COLOR_BORDER)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(self.sidebar, text="⚡ ADMIN PORTAL", font=css.FONT_SECTION, text_color=css.COLOR_TEXT_MAIN).pack(pady=(25, 4))
        ctk.CTkLabel(self.sidebar, text="HỆ THỐNG QUẢN TRỊ ĐỀ THI", font=css.FONT_BADGE, text_color=css.COLOR_ACCENT).pack(pady=(0, 25))

        self.btn_nav_topics = ctk.CTkButton(self.sidebar, text="📚  Đề Tài & Câu Hỏi", font=css.FONT_BODY_BOLD,
                                            height=42, corner_radius=8, fg_color="#EFF6FF", text_color=css.COLOR_ACCENT, hover_color="#DBEAFE",
                                            anchor="w", command=lambda: self.switch_view("TOPICS"))
        self.btn_nav_topics.pack(fill="x", padx=15, pady=5)

        self.btn_nav_exams = ctk.CTkButton(self.sidebar, text="⏱  Kỳ Thi Trực Tuyến", font=css.FONT_BODY_BOLD,
                                           height=42, corner_radius=8, fg_color="transparent", text_color=css.COLOR_TEXT_MAIN, hover_color="#F1F5F9",
                                           anchor="w", command=lambda: self.switch_view("EXAMS"))
        self.btn_nav_exams.pack(fill="x", padx=15, pady=5)

        self.btn_nav_proctor = ctk.CTkButton(self.sidebar, text="👁  Giám Sát Phòng Thi", font=css.FONT_BODY_BOLD,
                                            height=42, corner_radius=8, fg_color="transparent", text_color=css.COLOR_TEXT_MAIN, hover_color="#F1F5F9",
                                            anchor="w", command=lambda: self.switch_view("PROCTOR"))
        self.btn_nav_proctor.pack(fill="x", padx=15, pady=5)

        self.btn_nav_chat = ctk.CTkButton(self.sidebar, text="💬  Kênh Trò Chuyện", font=css.FONT_BODY_BOLD,
                                          height=42, corner_radius=8, fg_color="transparent", text_color=css.COLOR_TEXT_MAIN, hover_color="#F1F5F9",
                                          anchor="w", command=lambda: self.switch_view("CHAT"))
        self.btn_nav_chat.pack(fill="x", padx=15, pady=5)

        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.pack(side="right", fill="both", expand=True, padx=25, pady=20)

        self.switch_view("TOPICS")

    def switch_view(self, view_name):
        for w in self.main_content.winfo_children():
            w.destroy()

        self.btn_nav_topics.configure(fg_color="transparent", text_color=css.COLOR_TEXT_MAIN)
        self.btn_nav_exams.configure(fg_color="transparent", text_color=css.COLOR_TEXT_MAIN)
        self.btn_nav_proctor.configure(fg_color="transparent", text_color=css.COLOR_TEXT_MAIN)
        self.btn_nav_chat.configure(fg_color="transparent", text_color=css.COLOR_TEXT_MAIN)

        if view_name == "TOPICS":
            self.btn_nav_topics.configure(fg_color="#EFF6FF", text_color=css.COLOR_ACCENT)
            view = TopicView(self.main_content, self.db)
        elif view_name == "EXAMS":
            self.btn_nav_exams.configure(fg_color="#EFF6FF", text_color=css.COLOR_ACCENT)
            view = ExamView(self.main_content, self.db)
        elif view_name == "PROCTOR":
            self.btn_nav_proctor.configure(fg_color="#EFF6FF", text_color=css.COLOR_ACCENT)
            view = ProctorView(self.main_content, self.db, server_ip="192.168.1.26")
        elif view_name == "CHAT":
            self.btn_nav_chat.configure(fg_color="#EFF6FF", text_color=css.COLOR_ACCENT)
            view = AdminChatView(self.main_content)
            
        view.pack(fill="both", expand=True)

if __name__ == "__main__":
    app = AdminMasterApp()
    app.mainloop()