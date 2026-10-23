import customtkinter as ctk
import sys
import os

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from server.database import Database

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

class AdminMasterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("QUẢN TRỊ ĐÀO TẠO TIẾNG ANH • ADMIN WORKSPACE")
        self.geometry("1100x740")
        self.minsize(1020, 680)
        self.configure(fg_color=css.COLOR_BG)

        self.db = Database()
        self.current_chat_view = None
        self.setup_ui()

    def setup_ui(self):
        # Sidebar bên trái
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

        # Tab Trò Chuyện Trực Tiếp
        self.btn_nav_chat = ctk.CTkButton(self.sidebar, text="💬  Kênh Trò Chuyện", font=css.FONT_BODY_BOLD,
                                          height=42, corner_radius=8, fg_color="transparent", text_color=css.COLOR_TEXT_MAIN, hover_color="#F1F5F9",
                                          anchor="w", command=lambda: self.switch_view("CHAT"))
        self.btn_nav_chat.pack(fill="x", padx=15, pady=5)

        # Vùng nội dung chính
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.pack(side="right", fill="both", expand=True, padx=25, pady=20)

        self.switch_view("TOPICS")

    def switch_view(self, view_name):
        # Dọn sạch các view cũ
        for w in self.main_content.winfo_children():
            w.destroy()

        # Reset màu sắc nút menu
        self.btn_nav_topics.configure(fg_color="transparent", text_color=css.COLOR_TEXT_MAIN)
        self.btn_nav_exams.configure(fg_color="transparent", text_color=css.COLOR_TEXT_MAIN)
        self.btn_nav_chat.configure(fg_color="transparent", text_color=css.COLOR_TEXT_MAIN)

        if view_name == "TOPICS":
            self.btn_nav_topics.configure(fg_color="#EFF6FF", text_color=css.COLOR_ACCENT)
            view = TopicView(self.main_content, self.db)
        elif view_name == "EXAMS":
            self.btn_nav_exams.configure(fg_color="#EFF6FF", text_color=css.COLOR_ACCENT)
            view = ExamView(self.main_content, self.db)
        elif view_name == "CHAT":
            self.btn_nav_chat.configure(fg_color="#EFF6FF", text_color=css.COLOR_ACCENT)
            view = AdminChatView(self.main_content)
            
        view.pack(fill="both", expand=True)

if __name__ == "__main__":
    app = AdminMasterApp()
    app.mainloop()