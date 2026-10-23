import json

def send_msg(sock, data_dict):
    """Gửi một message JSON có gắn kèm ký tự kết thúc dòng \n"""
    payload = (json.dumps(data_dict, ensure_ascii=False) + "\n").encode('utf-8')
    sock.sendall(payload)

def recv_msg(sock):
    """Nhận trọn vẹn một gói tin dựa vào ký tự ngắt dòng \n"""
    buffer = ""
    while "\n" not in buffer:
        chunk = sock.recv(4096).decode('utf-8', errors='ignore')
        if not chunk:
            return None
        buffer += chunk
    line = buffer.split("\n", 1)[0]
    return json.loads(line)