import socket
import threading
import sys
import os
import traceback
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

active_clients = {}  # conn -> student_name
proctor_data = {}    # student_name -> dict(exam_title, status, time_left, violations, last_seen)
clients_lock = threading.Lock()

def broadcast_message(message_data):
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

def broadcast_proctor_update():
    """Gửi cập nhật trạng thái phòng thi tới các máy giám sát Admin"""
    packet = {
        "type": "PROCTOR_BROADCAST",
        "students": list(proctor_data.values())
    }
    broadcast_message(packet)

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

            # --- 1. XỬ LÝ ĐĂNG KÝ TÀI KHOẢN MỚI ---
            if action == "REGISTER_ACCOUNT":
                u_name = msg.get("username", "").strip()
                p_word = msg.get("password", "").strip()
                f_name = msg.get("full_name", "").strip()

                if not u_name or not p_word or not f_name:
                    send_msg(conn, {"status": "ERROR", "message": "Vui lòng điền đầy đủ thông tin!"})
                else:
                    ok, res_msg = db.register_user(u_name, p_word, f_name)
                    if ok:
                        send_msg(conn, {"status": "SUCCESS", "type": "REGISTER_ACCOUNT_OK", "message": res_msg})
                    else:
                        send_msg(conn, {"status": "ERROR", "message": res_msg})

            # --- 2. XỬ LÝ ĐĂNG NHẬP THÍ SINH ---
            elif action == "LOGIN_USER":
                u_name = msg.get("username", "").strip()
                p_word = msg.get("password", "").strip()

                ok, user_data = db.authenticate_user(u_name, p_word)
                if ok:
                    current_user = user_data["full_name"]
                    with clients_lock:
                        active_clients[conn] = current_user

                    send_msg(conn, {
                        "status": "SUCCESS",
                        "type": "LOGIN_OK",
                        "username": user_data["username"],
                        "full_name": user_data["full_name"]
                    })

                    join_packet = {
                        "type": "CHAT_BROADCAST",
                        "sender": "HỆ THỐNG",
                        "text": f"Thí sinh '{current_user}' đã đăng nhập vào hệ thống.",
                        "time": datetime.now().strftime("%H:%M")
                    }
                    broadcast_message(join_packet)
                else:
                    send_msg(conn, {"status": "ERROR", "message": "Sai tên đăng nhập hoặc mật khẩu!"})

            # --- 3. ĐĂNG KÝ KẾT NỐI GIÁM SÁT / NGƯỜI DÙNG CŨ ---
            elif action == "REGISTER_USER":
                current_user = msg.get("student_name", "Ẩn danh")
                with clients_lock:
                    active_clients[conn] = current_user
                
                print(f"[+] '{current_user}' đã kết nối từ {addr}")
                send_msg(conn, {"status": "SUCCESS", "type": "REGISTER_OK"})
                
                if current_user != "Admin_Supervisor":
                    join_packet = {
                        "type": "CHAT_BROADCAST",
                        "sender": "HỆ THỐNG",
                        "text": f"Thí sinh '{current_user}' đã tham gia phòng thi.",
                        "time": datetime.now().strftime("%H:%M")
                    }
                    broadcast_message(join_packet)

            # --- 4. BẮT ĐẦU LÀM BÀI THI ---
            elif action == "START_EXAM_STATUS":
                student = msg.get("student_name", current_user)
                exam_title = msg.get("exam_title", "Chưa rõ")
                time_left = msg.get("time_left", 0)
                with clients_lock:
                    proctor_data[student] = {
                        "name": student,
                        "exam_title": exam_title,
                        "status": "ĐANG LÀM BÀI",
                        "time_left": time_left,
                        "violations": 0,
                        "last_update": datetime.now().strftime("%H:%M:%S")
                    }
                broadcast_proctor_update()

            # --- 5. HEARTBEAT CẬP NHẬT THỜI GIAN CÒN LẠI ---
            elif action == "HEARTBEAT":
                student = msg.get("student_name", current_user)
                time_left = msg.get("time_left", 0)
                with clients_lock:
                    if student in proctor_data:
                        proctor_data[student]["time_left"] = time_left
                        proctor_data[student]["last_update"] = datetime.now().strftime("%H:%M:%S")
                broadcast_proctor_update()

            # --- 6. BÁO CÁO VI PHẠM RỜI TAB (ALT+TAB) ---
            elif action == "REPORT_VIOLATION":
                student = msg.get("student_name", current_user)
                count = msg.get("violations", 1)
                with clients_lock:
                    if student in proctor_data:
                        proctor_data[student]["violations"] = count
                        proctor_data[student]["last_update"] = datetime.now().strftime("%H:%M:%S")
                broadcast_proctor_update()

            # --- 7. LẤY DỮ LIỆU GIÁM SÁT CHO ADMIN ---
            elif action == "GET_PROCTOR_DATA":
                with clients_lock:
                    send_msg(conn, {
                        "status": "SUCCESS",
                        "type": "PROCTOR_BROADCAST",
                        "students": list(proctor_data.values())
                    })

            # --- 8. TIN NHẮN CHAT ---
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

            # --- 9. LẤY DANH SÁCH ĐỀ THI ---
            elif action == "GET_EXAMS":
                student_name = msg.get("student_name", "")
                try:
                    exams = db.get_active_exams_for_student()
                    for ex in exams:
                        try:
                            past = db.get_student_result_for_exam(ex["id"], student_name)
                            ex["is_completed"] = bool(past)
                            ex["past_score"] = past["score"] if past else None
                            ex["past_correct"] = past["correct_count"] if past else None
                        except Exception:
                            ex["is_completed"] = False
                            ex["past_score"] = None
                            ex["past_correct"] = None
                    send_msg(conn, {"status": "SUCCESS", "type": "EXAMS_DATA", "exams": exams})
                except Exception as db_err:
                    print(f"[-] Lỗi GET_EXAMS: {db_err}")
                    traceback.print_exc()
                    send_msg(conn, {"status": "SUCCESS", "type": "EXAMS_DATA", "exams": []})

            # --- 10. LẤY CÂU HỎI THI ---
            elif action == "GET_QUESTIONS":
                try:
                    topic_id = msg.get("topic_id")
                    questions = db.get_exam_questions(topic_id)
                    send_msg(conn, {"status": "SUCCESS", "type": "QUESTIONS_DATA", "questions": questions})
                except Exception as q_err:
                    print(f"[-] Lỗi GET_QUESTIONS: {q_err}")
                    send_msg(conn, {"status": "ERROR", "type": "QUESTIONS_DATA", "questions": []})

            # --- 11. NỘP BÀI THI & LƯU SỐ LẦN VI PHẠM ---
            elif action == "SUBMIT_EXAM":
                student = msg.get("student_name", current_user)
                viol = msg.get("violations", 0)
                try:
                    db.save_exam_result(
                        exam_id=msg["exam_id"],
                        student_name=student,
                        correct_count=msg["correct_count"],
                        total_questions=msg["total_questions"],
                        score=msg["score"],
                        violations=viol
                    )
                    send_msg(conn, {"status": "SUCCESS", "type": "SUBMIT_OK"})
                    with clients_lock:
                        if student in proctor_data:
                            proctor_data[student]["status"] = f"ĐÃ NỘP ({msg['score']}/10)"
                            proctor_data[student]["time_left"] = 0
                            proctor_data[student]["violations"] = viol
                    broadcast_proctor_update()
                except Exception as s_err:
                    print(f"[-] Lỗi SUBMIT_EXAM: {s_err}")
                    send_msg(conn, {"status": "ERROR", "type": "SUBMIT_OK", "message": str(s_err)})

    except Exception:
        pass
    finally:
        with clients_lock:
            if conn in active_clients:
                left_user = active_clients.pop(conn)
                if left_user and left_user not in ["Ẩn danh", "Admin_Supervisor"]:
                    print(f"[-] Thí sinh '{left_user}' đã ngắt kết nối.")
                    if left_user in proctor_data and not proctor_data[left_user]["status"].startswith("ĐÃ NỘP"):
                        proctor_data[left_user]["status"] = "RỜI PHÒNG (Mất mạng)"
                    leave_packet = {
                        "type": "CHAT_BROADCAST",
                        "sender": "HỆ THỐNG",
                        "text": f"Thí sinh '{left_user}' đã rời phòng thi.",
                        "time": datetime.now().strftime("%H:%M")
                    }
                    broadcast_message(leave_packet)
                    broadcast_proctor_update()
        try:
            conn.close()
        except Exception:
            pass

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(50)
    print("==================================================")
    print(f"🚀 SERVER LIVE PROCTORING DANG CHAY TREN PORT {PORT}")
    print("==================================================")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()