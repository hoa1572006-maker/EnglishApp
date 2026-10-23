import socket
import threading
import sys
import os
from datetime import datetime

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_dir not in sys.path:
    sys.path.append(base_dir)

try:
    from database import Database
except ModuleNotFoundError:
    from server.database import Database

from shared.protocol import send_msg, recv_msg

HOST = "0.0.0.0"
PORT = 8888

db = Database()
active_clients = {}
clients_lock = threading.Lock()

def broadcast_message(message_data):
    """Gửi một gói tin đến toàn bộ các kết nối socket đang online"""
    with clients_lock:
        dead_conns = []
        for client_conn in list(active_clients.keys()):
            try:
                send_msg(client_conn, message_data)
            except Exception:
                dead_conns.append(client_conn)
        for dead in dead_conns:
            if dead in active_clients:
                del active_clients[dead]

def handle_client(conn, addr):
    current_user = "Ẩn danh"
    with clients_lock:
        active_clients[conn] = current_user

    try:
        while True:
            msg = recv_msg(conn)
            if not msg:
                break
            
            action = msg.get("action")

            # Đăng ký danh tính người kết nối
            if action == "REGISTER_USER":
                current_user = msg.get("student_name", "Ẩn danh")
                with clients_lock:
                    active_clients[conn] = current_user
                
                # In thông báo ra màn hình terminal của Server
                print(f"[+] Thí sinh '{current_user}' đã kết nối từ địa chỉ {addr}")

                # Phát tin nhắn hệ thống vào khung chat cho Admin và các máy cùng thấy
                join_packet = {
                    "type": "CHAT_BROADCAST",
                    "sender": "HỆ THỐNG",
                    "text": f"Thí sinh '{current_user}' đã tham gia phòng thi.",
                    "time": datetime.now().strftime("%H:%M")
                }
                broadcast_message(join_packet)

            # Xử lý tin nhắn chat và phát broadcast tới tất cả các bên
            elif action == "SEND_CHAT":
                sender = msg.get("sender", current_user)
                text = msg.get("text", "").strip()
                if text:
                    packet = {
                        "type": "CHAT_BROADCAST",
                        "sender": sender,
                        "text": text,
                        "time": datetime.now().strftime("%H:%M")
                    }
                    broadcast_message(packet)

            # Lấy danh sách kỳ thi
            elif action == "GET_EXAMS":
                student_name = msg.get("student_name", "")
                exams = db.get_active_exams_for_student()
                for ex in exams:
                    past = db.get_student_result_for_exam(ex["id"], student_name)
                    ex["is_completed"] = bool(past)
                    ex["past_score"] = past["score"] if past else None
                    ex["past_correct"] = past["correct_count"] if past else None
                send_msg(conn, {"status": "SUCCESS", "exams": exams})

            # Lấy câu hỏi đề thi
            elif action == "GET_QUESTIONS":
                topic_id = msg.get("topic_id")
                questions = db.get_exam_questions(topic_id)
                send_msg(conn, {"status": "SUCCESS", "questions": questions})

            # Nộp bài thi
            elif action == "SUBMIT_EXAM":
                db.save_exam_result(
                    exam_id=msg["exam_id"],
                    student_name=msg["student_name"],
                    correct_count=msg["correct_count"],
                    total_questions=msg["total_questions"],
                    score=msg["score"]
                )
                send_msg(conn, {"status": "SUCCESS", "message": "OK"})

    except Exception:
        pass
    finally:
        with clients_lock:
            if conn in active_clients:
                left_user = active_clients.pop(conn)
                if left_user and left_user != "Ẩn danh":
                    print(f"[-] Thí sinh '{left_user}' đã ngắt kết nối.")
                    leave_packet = {
                        "type": "CHAT_BROADCAST",
                        "sender": "HỆ THỐNG",
                        "text": f"Thí sinh '{left_user}' đã rời phòng thi.",
                        "time": datetime.now().strftime("%H:%M")
                    }
                    broadcast_message(leave_packet)
        conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(50)
    print("==================================================")
    print(f"🚀 SERVER DANG CHAY TREN PORT {PORT} (DA BAT CHAT)")
    print("==================================================")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()