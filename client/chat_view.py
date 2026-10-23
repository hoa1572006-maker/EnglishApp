import customtkinter as ctk
from datetime import datetime
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

class AdminChatView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.sock = None
        self.is_connected = False
        self.is_listening = False
        self.server_port = 8888
        self.active_ip = "127.0.0.1"

        self.setup_ui()
        self.connect_to_server()

    def setup_ui(self):
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(top_bar, text="KÊNH TRÒ CHUYỆN & ĐIỀU HÀNH PHÒNG THI", font=css.FONT_TITLE, text_color=css.COLOR_TEXT_MAIN).pack(side="left")
        
        self.lbl_status = ctk.CTkLabel(top_bar, text="Đang kết nối...", font=css.FONT_BADGE, text_color=css.COLOR_WARNING, fg_color="#FEF3C7", corner_radius=6, padx=10, pady=3)
        self.lbl_status.pack(side="right")

        self.chat_container = ctk.CTkFrame(self, **css.STYLE_CARD)
        self.chat_container.pack(fill="both", expand=True, pady=(0, 10))

        self.scroll_chat = ctk.CTkScrollableFrame(self.chat_container, fg_color="transparent")
        self.scroll_chat.pack(fill="both", expand=True, padx=12, pady=10)

        input_bar = ctk.CTkFrame(self, fg_color="transparent")
        input_bar.pack(fill="x")

        self.in_msg = ctk.CTkEntry(input_bar, placeholder_text="Nhập thông báo hoặc trả lời thí sinh (Enter để gửi)...", **css.STYLE_ENTRY)
        self.in_msg.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.in_msg.bind("<Return>", lambda e: self.send_message())

        self.btn_send = ctk.CTkButton(input_bar, text="📢 Phát Thông Báo", width=140, **css.STYLE_PRIMARY_BTN, command=self.send_message)
        self.btn_send.pack(side="right")

    def connect_to_server(self):
        def connect_thread():
            connected = False
            for ip in ["127.0.0.1", "10.60.14.113", "192.168.1.26"]:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1.5)
                    s.connect((ip, self.server_port))
                    s.settimeout(None)
                    self.sock = s
                    connected = True
                    self.active_ip = ip
                    break
                except Exception:
                    continue

            if connected:
                self.is_connected = True
                send_msg(self.sock, {"action": "REGISTER_USER", "student_name": "Admin (Giáo viên)"})
                self.after(0, lambda: self.lbl_status.configure(text=f"🟢 Đã kết nối Socket ({self.active_ip})", text_color="#15803D", fg_color="#DCFCE7"))
                
                welcome_msg = {
                    "type": "CHAT_BROADCAST",
                    "sender": "HỆ THỐNG",
                    "text": "Phòng điều hành đã sẵn sàng. Mọi tin nhắn sẽ hiển thị tại đây.",
                    "time": datetime.now().strftime("%H:%M")
                }
                self.after(0, self.append_message, welcome_msg)

                self.is_listening = True
                while self.is_listening:
                    try:
                        msg = recv_msg(self.sock)
                        if not msg:
                            break
                        if msg.get("type") == "CHAT_BROADCAST":
                            self.after(0, self.append_message, msg)
                    except Exception:
                        break
            else:
                self.after(0, lambda: self.lbl_status.configure(text="🔴 Server chưa bật", text_color=css.COLOR_DANGER, fg_color="#FEE2E2"))

        threading.Thread(target=connect_thread, daemon=True).start()

    def send_message(self):
        text = self.in_msg.get().strip()
        if not text or not self.is_connected or not self.sock:
            return

        try:
            send_msg(self.sock, {
                "action": "SEND_CHAT",
                "sender": "Admin (Giáo viên)",
                "text": text
            })
            self.in_msg.delete(0, "end")
        except Exception:
            self.lbl_status.configure(text="🔴 Mất kết nối", text_color=css.COLOR_DANGER, fg_color="#FEE2E2")

    def append_message(self, msg):
        if not hasattr(self, 'scroll_chat') or not self.scroll_chat.winfo_exists():
            return

        sender = msg.get("sender", "")
        text = msg.get("text", "")
        send_time = msg.get("time", "")

        is_admin = ("Admin" in sender)
        is_sys = (sender == "HỆ THỐNG")

        card = ctk.CTkFrame(self.scroll_chat, corner_radius=8, border_width=1, border_color=css.COLOR_BORDER)
        card.pack(fill="x", pady=4, padx=4)

        if is_sys:
            card.configure(fg_color="#FEF3C7", border_color="#FDE68A")
            ctk.CTkLabel(card, text=f"📢 {text}", font=css.FONT_BADGE, text_color="#92400E", wraplength=680, justify="left").pack(anchor="w", padx=10, pady=6)
        elif is_admin:
            card.configure(fg_color="#EFF6FF", border_color="#BFDBFE")
            ctk.CTkLabel(card, text=f"👑 {sender} ({send_time})", font=css.FONT_BODY_BOLD, text_color=css.COLOR_ACCENT).pack(anchor="w", padx=10, pady=(6, 1))
            ctk.CTkLabel(card, text=text, font=css.FONT_BODY, text_color=css.COLOR_TEXT_MAIN, wraplength=680, justify="left").pack(anchor="w", padx=10, pady=(0, 6))
        else:
            card.configure(fg_color=css.COLOR_CARD_ALT)
            ctk.CTkLabel(card, text=f"👤 {sender} ({send_time})", font=css.FONT_BADGE, text_color="#0F766E").pack(anchor="w", padx=10, pady=(6, 1))
            ctk.CTkLabel(card, text=text, font=css.FONT_BODY, text_color=css.COLOR_TEXT_MAIN, wraplength=680, justify="left").pack(anchor="w", padx=10, pady=(0, 6))

    def destroy(self):
        self.is_listening = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        super().destroy()