"""
theme.py - Thiết lập bảng màu sáng (Modern Light UI) và quy chuẩn giao diện
"""

# Bảng màu sáng (Modern Clean Light)
COLOR_BG = "#F4F6F9"             # Nền chính xám trắng nhẹ dịu mắt
COLOR_SIDEBAR = "#FFFFFF"        # Nền Sidebar trắng thanh lịch
COLOR_CARD = "#FFFFFF"           # Nền các thẻ Card trắng sáng
COLOR_CARD_ALT = "#F8FAFC"       # Nền thẻ danh sách / phụ
COLOR_BORDER = "#E2E8F0"         # Viền xám nhạt tinh tế
COLOR_INPUT_BG = "#FFFFFF"       # Màu nền ô nhập

# Màu sắc điểm nhấn & Trạng thái
COLOR_ACCENT = "#2563EB"         # Xanh dương công nghệ (Royal Blue)
COLOR_SUCCESS = "#16A34A"        # Xanh lá cây tự nhiên (Green Emerald)
COLOR_DANGER = "#DC2626"         # Đỏ cảnh báo nổi bật
COLOR_WARNING = "#D97706"        # Cam hổ phách
COLOR_TEXT_MAIN = "#1E293B"      # Màu chữ chính (Slate 800 - đậm, rõ nét)
COLOR_TEXT_MUTED = "#64748B"     # Màu chữ phụ / chú thích (Slate 500)

# Quy chuẩn Font chữ
FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_SECTION = ("Segoe UI", 15, "bold")
FONT_SUBTITLE = ("Segoe UI", 12)
FONT_BODY_BOLD = ("Segoe UI", 13, "bold")
FONT_BODY = ("Segoe UI", 13)
FONT_BADGE = ("Segoe UI", 11, "bold")

# Preset cấu hình các Widget
STYLE_PRIMARY_BTN = {
    "font": FONT_BODY_BOLD,
    "height": 38,
    "corner_radius": 8,
    "fg_color": COLOR_ACCENT,
    "hover_color": "#1D4ED8",
    "text_color": "#FFFFFF"
}

STYLE_SUCCESS_BTN = {
    "font": FONT_BODY_BOLD,
    "height": 38,
    "corner_radius": 8,
    "fg_color": COLOR_SUCCESS,
    "hover_color": "#15803D",
    "text_color": "#FFFFFF"
}

STYLE_DANGER_BTN = {
    "font": FONT_BADGE,
    "height": 28,
    "corner_radius": 6,
    "fg_color": "#FEE2E2",
    "text_color": "#B91C1C",
    "hover_color": "#FCA5A5"
}

STYLE_ENTRY = {
    "height": 38,
    "corner_radius": 8,
    "font": FONT_BODY,
    "fg_color": COLOR_INPUT_BG,
    "text_color": COLOR_TEXT_MAIN,
    "border_color": COLOR_BORDER,
    "border_width": 1.5
}

STYLE_CARD = {
    "fg_color": COLOR_CARD,
    "corner_radius": 12,
    "border_width": 1,
    "border_color": COLOR_BORDER
}