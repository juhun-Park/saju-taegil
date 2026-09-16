# -*- coding: utf-8 -*-
"""AI 택일 상담 — 대화형 웹앱(Streamlit)
실행: 이 폴더에서  streamlit run web_app.py
필요: pip install streamlit google-genai lunar_python python-dotenv
(agent.py, taegil_engine.py 가 같은 폴더에 있어야 함)"""
import os, datetime
import streamlit as st
# 배포(Streamlit Cloud)에선 Secrets로 키가 들어옴 → 환경변수로 옮겨 agent가 읽게 함
try:
    if "GEMINI_API_KEY" in st.secrets:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
    if "GEMINI_MODEL" in st.secrets:
        os.environ["GEMINI_MODEL"] = st.secrets["GEMINI_MODEL"]
except Exception:
    pass
import agent  # 대화형 에이전트

# 예약 접수용 Google Apps Script 웹앱 URL (Secrets에 넣으면 그걸 우선 사용)
BOOKING_WEBHOOK = "https://script.google.com/macros/s/AKfycbx66nJHcgl_pmQGRjThrCRdbyl_HUFB2pN4Egzb1EgH5wXc9iQ9VqZUen-VPZt2hYqSDQ/exec"
try:
    if "BOOKING_WEBHOOK" in st.secrets:
        BOOKING_WEBHOOK = st.secrets["BOOKING_WEBHOOK"]
except Exception:
    pass

def send_booking_to_sheet(data):
    """예약 정보를 구글 시트로 전송. 성공하면 True."""
    import json, urllib.request
    try:
        req = urllib.request.Request(
            BOOKING_WEBHOOK,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False

# ---------- 리포트 PDF 생성 (동인 브랜드) ----------
@st.cache_data(show_spinner=False)
def _ensure_font():
    """Noto Sans KR 폰트 확보(없으면 다운로드). 경로 반환."""
    import os, urllib.request
    path = "NotoSansKR-Regular.ttf"
    if os.path.exists(path):
        return path
    try:
        urllib.request.urlretrieve(
            "https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf",
            path)
        return path
    except Exception:
        return None

def make_report_pdf(title, body_text, dosa_img=None):
    """리포트를 크림 배경 브랜드 PDF(bytes)로. 실패 시 None."""
    import re, os
    try:
        from fpdf import FPDF
    except Exception:
        return None
    font = _ensure_font()
    if not font or not os.path.exists(font):
        return None
    def strip_emoji(s):
        return re.sub(r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\u2190-\u21FF\u2B00-\u2BFF\uFE0F]', '', s)
    pdf = FPDF(format="A4"); pdf.add_page()
    pdf.add_font("KR", "", font); pdf.add_font("KR", "B", font)
    CREAM=(250,246,238); INK=(35,32,28); GOLD=(150,115,40); RED=(150,43,37)
    pdf.set_fill_color(*CREAM); pdf.rect(0,0,210,297,'F')
    pdf.set_fill_color(*RED); pdf.rect(0,0,210,24,'F')
    pdf.set_xy(12,6); pdf.set_font("KR","B",15); pdf.set_text_color(245,230,200)
    pdf.cell(0,11,"棟寅  동인 · AI 사주 상담"); pdf.ln(20)
    if dosa_img and os.path.exists(dosa_img):
        try: pdf.image(dosa_img, x=162, y=29, w=36, h=36)
        except Exception: pass
    pdf.set_xy(12,32); pdf.set_font("KR","B",17); pdf.set_text_color(*RED)
    pdf.multi_cell(140,9, strip_emoji(title).strip()); pdf.ln(1)
    pdf.set_draw_color(*GOLD); pdf.set_line_width(0.6)
    pdf.line(12,pdf.get_y()+1,198,pdf.get_y()+1); pdf.ln(6)
    for raw in body_text.split("\n"):
        line=strip_emoji(raw).rstrip()
        if not line.strip(): pdf.ln(2.5); continue
        m=re.match(r'^#{1,6}\s*(.+)', line)
        if pdf.get_y()>265:
            pdf.add_page(); pdf.set_fill_color(*CREAM); pdf.rect(0,0,210,297,'F')
        if m:
            pdf.ln(2); pdf.set_font("KR","B",12.5); pdf.set_text_color(*RED)
            pdf.set_x(12); pdf.multi_cell(186,7,m.group(1).strip()); pdf.ln(0.5)
        else:
            pdf.set_font("KR","",10.8); pdf.set_text_color(*INK)
            pdf.set_x(12); pdf.multi_cell(186,6.3,line)
    pdf.set_y(-15); pdf.set_font("KR","",8); pdf.set_text_color(150,140,120)
    pdf.set_x(12); pdf.cell(0,6,"동인 · AI 사주 상담   |   재미로 보는 명리 콘텐츠")
    return bytes(pdf.output())

# ---------- 이미지 로더: 한 번만 리사이즈·압축 후 캐시 ----------
@st.cache_data(show_spinner=False)
def load_card_image(cat, size=240):
    """images/dosa_{cat}.png 를 정사각 size로 줄이고 압축해 base64로 반환(캐시됨)."""
    import base64, os, io
    path = os.path.join("images", f"dosa_{cat}.png")
    if not os.path.exists(path):
        return ""
    try:
        from PIL import Image
        img = Image.open(path).convert("RGB")
        # 정사각형 중앙 크롭 후 축소
        w, h = img.size
        s = min(w, h)
        img = img.crop(((w-s)//2, (h-s)//2, (w-s)//2+s, (h-s)//2+s)).resize((size, size))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80, optimize=True)  # JPEG로 용량 대폭↓
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        # Pillow 없거나 오류 시: 원본을 그대로(압축 없이) 반환
        try:
            with open(path, "rb") as f:
                return "data:image/png;base64," + base64.b64encode(f.read()).decode()
        except Exception:
            return ""

st.set_page_config(page_title="동인 — AI 사주 상담", page_icon="🀄", layout="wide",
                   initial_sidebar_state="collapsed")

# ---------- 커스텀 테마 (Deep Midnight Navy + Gold + Glass) ----------
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

/* ===== 테마 고정: 라이트 모드에서도 항상 다크로 ===== */
:root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"],
[data-testid="stMain"], .main, .block-container {
  background-color:#0A0D14 !important;
  color:#E7E2D6 !important;
}
[data-testid="stHeader"]{ background:transparent !important; }
/* 모든 텍스트 요소 밝은색 강제 (두 테마 공통) */
.stApp, .stApp *, [data-testid="stSidebar"] * {
  color:#E7E2D6;
}
.stApp p, .stApp span, .stApp li, .stApp label, .stApp div,
.stMarkdown, .stMarkdown * { color:#E7E2D6 !important; }
h1,h2,h3,h4,h5,h6 { color:#F1ECE0 !important; }
/* 입력 위젯 내부 텍스트/배경도 다크 고정 */
input, textarea, select, .stNumberInput input, .stDateInput input,
[data-baseweb="input"] input, [data-baseweb="select"] * {
  color:#E7E2D6 !important;
  background-color:rgba(255,255,255,0.04) !important;
}
/* 라디오/체크박스 라벨 */
[data-testid="stRadio"] label, [data-testid="stCheckbox"] label,
[data-baseweb="radio"] *, [data-baseweb="checkbox"] * { color:#D8D2C4 !important; }
/* 드롭다운 팝업(라이트에서 흰 배경 뜨는 것) 다크로 */
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] {
  background-color:#14181F !important; color:#E7E2D6 !important;
}
[role="option"] { color:#E7E2D6 !important; }
/* 캘린더 팝업 */
[data-baseweb="calendar"] { background:#14181F !important; color:#E7E2D6 !important; }
[data-baseweb="calendar"] * { color:#E7E2D6 !important; }

/* 전체 배경 — 먹빛 네이비 + 오행 은은한 글로우 + 미세 격자 문양 */
.stApp {
  background:
    radial-gradient(900px 500px at 85% -8%, rgba(178,34,52,0.10), transparent 58%),
    radial-gradient(800px 460px at 0% 108%, rgba(197,160,94,0.09), transparent 55%),
    linear-gradient(180deg, #0C1018, #0A0D14);
  color: #E7E2D6;
  font-family: 'Pretendard','Inter',sans-serif;
}
/* 미세한 동양 격자(창살) 텍스처 */
.stApp::before{
  content:""; position:fixed; inset:0; pointer-events:none; opacity:0.035;
  background-image:linear-gradient(#C5A05E 1px, transparent 1px),
                   linear-gradient(90deg,#C5A05E 1px, transparent 1px);
  background-size:44px 44px;
}
/* 사이드바 */
section[data-testid="stSidebar"] > div {
  background: rgba(15,23,42,0.72);
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(255,255,255,0.08);
}
h1,h2,h3,h4 { font-family:'Pretendard','Inter',sans-serif; letter-spacing:-0.02em; }
h1 { background:linear-gradient(135deg,#E8C874,#C5A05E 55%,#B22234); -webkit-background-clip:text;
     -webkit-text-fill-color:transparent; font-weight:800; }

/* 입력 필드 */
.stDateInput input, .stNumberInput input, .stTextInput input {
  background: rgba(255,255,255,0.04)!important; color:#E7E2D6!important;
  border:1px solid rgba(197,160,94,0.20)!important; border-radius:12px!important;
}
.stDateInput input:focus, .stNumberInput input:focus {
  border-color:#C5A05E!important; box-shadow:0 0 0 3px rgba(197,160,94,0.25)!important;
}

/* 버튼 = 주사(朱砂) 붉은빛 + 금테 */
.stButton > button {
  background:linear-gradient(135deg,#9E2B25,#7A1E1E); color:#F5E6C8;
  border:1px solid rgba(197,160,94,0.55); border-radius:12px; font-weight:700;
  padding:0.6rem 1rem; transition:all .18s ease; letter-spacing:0.02em;
}
.stButton > button:hover {
  transform:translateY(-2px); color:#FFF3DA;
  box-shadow:0 4px 22px rgba(158,43,37,0.40); border-color:rgba(232,200,116,0.9);
}

/* 채팅 말풍선 = 글래스 카드 */
[data-testid="stChatMessage"] {
  background: rgba(255,255,255,0.04); backdrop-filter: blur(10px);
  border:1px solid rgba(255,255,255,0.08); border-radius:16px;
  padding:0.4rem 0.8rem; margin-bottom:0.4rem;
}
/* 성공/정보 박스 */
[data-testid="stAlert"] {
  background: rgba(255,255,255,0.04); border:1px solid rgba(197,160,94,0.28);
  border-radius:14px; color:#E2E8F0;
}
/* 배지 칩 */
.chip { display:inline-block; padding:4px 12px; margin:3px 4px;
  background:rgba(197,160,94,0.10); border:1px solid rgba(197,160,94,0.30);
  color:#E8C874; border-radius:999px; font-size:0.78rem; }
/* 퀵스타트 카드 */
.qcard { background:rgba(255,255,255,0.04); backdrop-filter:blur(10px);
  border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:18px 18px;
  margin-bottom:14px; transition:all .18s ease; }
.qcard:hover { border-color:rgba(197,160,94,0.5); transform:translateY(-2px);
  box-shadow:0 6px 24px rgba(158,43,37,0.14); }
.qcard .t { color:#F1F5F9; font-weight:700; font-size:1.02rem; margin-bottom:4px; }
.qcard .d { color:#94A3B8; font-size:0.86rem; line-height:1.45; }
.chat-input-hint { color:#64748B; font-size:0.82rem; }

/* 입력칸 예시(placeholder) 회색으로 잘 보이게 */
input::placeholder, textarea::placeholder {
  color:#7A8394 !important; opacity:1 !important;
}

/* ===== 클릭 가능한 이미지 카테고리 카드 ===== */
.cat-card{
  position:relative;
  background:rgba(255,255,255,0.045);
  border:1px solid rgba(255,255,255,0.09);
  border-radius:18px; overflow:hidden;
  transition:all .18s ease;
  display:flex; align-items:stretch;   /* 가로 배치 */
}
.cat-card:hover{
  border-color:rgba(197,160,94,0.6); transform:translateY(-3px);
  box-shadow:0 8px 26px rgba(158,43,37,0.20);
}
.cat-card .cc-img{
  width:104px; min-width:104px; height:104px; object-fit:cover; display:block;
  border-right:1px solid rgba(255,255,255,0.06);
}
.cat-card .cc-body{ padding:12px 14px; flex:1; display:flex; flex-direction:column; justify-content:center; }
.cat-card .cc-top{ display:flex; justify-content:space-between; align-items:center; gap:6px; }
.cat-card .cc-title{ font-size:1.02rem; font-weight:800; color:#F5F0E4; letter-spacing:-0.01em; }
.cat-card .cc-price{
  font-size:0.76rem; font-weight:800; color:#E8C874;
  background:rgba(197,160,94,0.12); border:1px solid rgba(197,160,94,0.35);
  border-radius:999px; padding:2px 9px; white-space:nowrap;
}
.cat-card .cc-desc{ margin-top:5px; color:#AEB6C2; font-size:0.82rem; line-height:1.4; }

/* 홈·뒤로 내비 버튼 — 작고 수수하게 */
div[data-testid="column"]:nth-of-type(1) .stButton > button[key="home"],
div[data-testid="column"]:nth-of-type(2) .stButton > button[key="back"]{
  background:rgba(255,255,255,0.05) !important;
  border:1px solid rgba(255,255,255,0.12) !important;
  color:#CBD5E1 !important; font-weight:600 !important;
}
/* 카드 아래 '보기' 버튼 — 카드와 자연스럽게 이어지게 */
div[data-testid="column"] .stButton > button{
  background:rgba(197,160,94,0.10) !important;
  border:1px solid rgba(197,160,94,0.35) !important;
  color:#E8C874 !important; font-weight:700 !important;
  border-radius:12px !important; margin-top:-6px;
}
div[data-testid="column"] .stButton > button:hover{
  background:rgba(158,43,37,0.25) !important;
  border-color:rgba(232,200,116,0.8) !important; color:#FFF3DA !important;
  transform:translateY(-1px);
}


/* 텍스트 대비 강제 (모바일에서 글자가 배경에 묻히는 문제 해결) */
.stApp, .stApp p, .stApp span, .stApp label, .stApp li, .stApp div {
  color:#E2E8F0;
}
.stMarkdown, [data-testid="stChatMessage"] * { color:#E9EEF7 !important; }
label, .stCheckbox label, .stNumberInput label, .stDateInput label { color:#CBD5E1 !important; }
h1,h2,h3,h4,h5 { color:#F1F5F9; }
/* 위젯 내부 값 텍스트도 밝게 */
.stNumberInput input, .stDateInput input, .stSelectbox div { color:#E2E8F0 !important; }

/* 사이드바 토글 버튼(펼치기 »· 접기 «) 항상 눈에 잘 띄게 — 전 화면 공통 */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebar"] button[kind="header"],
[data-testid="baseButton-headerNoPadding"]{
  background:linear-gradient(135deg,#9E2B25,#7A1E1E) !important;
  border:1px solid rgba(232,200,116,0.85) !important;
  border-radius:10px !important; padding:6px !important;
  box-shadow:0 2px 12px rgba(158,43,37,0.5) !important;
  opacity:1 !important; visibility:visible !important;
}
/* 아이콘(화살표) 밝은 금색·크게, 두 버튼 동일하게 */
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebar"] button[kind="header"] svg{
  color:#FFF3DA !important; fill:#FFF3DA !important;
  width:24px !important; height:24px !important; opacity:1 !important;
}
/* 펼치기 버튼(>>): 닫혔을 때 왼쪽 위에 고정 + 크기 확보 */
[data-testid="stSidebarCollapsedControl"]{
  position:fixed !important; top:12px !important; left:12px !important; z-index:999 !important;
  opacity:1 !important; transform:none !important;
  width:44px !important; height:44px !important;
  display:flex !important; align-items:center !important; justify-content:center !important;
}

/* 모바일 전용 보정 */
@media (max-width: 768px) {
  /* 본문 글자 살짝 키워 가독성 */
  .stApp p, .stApp li { font-size:0.98rem; line-height:1.6; }
  h1 { font-size:1.5rem !important; }
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div style='display:flex;align-items:center;gap:12px'>"
            "<span style='display:inline-flex;align-items:center;justify-content:center;"
            "width:46px;height:46px;border-radius:8px;background:linear-gradient(135deg,#9E2B25,#7A1E1E);"
            "border:1px solid rgba(232,200,116,0.7);color:#F5E6C8;font-weight:800;font-size:0.95rem;"
            "line-height:1.0;letter-spacing:-1px'>棟寅</span>"
            "<h1 style='margin:0'>동인 · AI 사주 상담</h1></div>", unsafe_allow_html=True)
st.markdown("<span style='color:#C5A05E;font-size:0.82rem'>● 명리 정밀 엔진 · 택일 · 시기운 · 적성 · 건강 · 성격 · 궁합</span>",
            unsafe_allow_html=True)
st.write("")

# ---------- 원국 입력 (본문 상단, 접이식) ----------
_has_pf = "profile" in st.session_state
if _has_pf:
    pr = st.session_state.profile
    _label = f"🔧 내 사주 정보: {pr['ganji']} · {pr.get('gender','')}  (변경하려면 여기를 누르세요)"
else:
    _label = "🧭 여기를 눌러 먼저 사주 정보를 입력하세요"

with st.expander(_label, expanded=not _has_pf):
    st.markdown("<span style='color:#94A3B8;font-size:0.85rem'>정밀한 분석을 위해 "
                "대상자의 사주 정보를 입력하세요.</span>", unsafe_allow_html=True)
    today = datetime.date.today()
    ci1, ci2 = st.columns([1,1])
    with ci1:
        cal_type = st.radio("달력", ["양력", "음력", "음력(윤달)"], horizontal=True)
        bd = st.date_input("생년월일", value=datetime.date(1990, 1, 1),
                           min_value=datetime.date(1930, 1, 1), max_value=today,
                           format="YYYY-MM-DD")
        if cal_type != "양력":
            st.caption("※ 입력한 날짜를 음력으로 보고 양력으로 자동 변환합니다.")
    with ci2:
        gender_label = st.radio("성별", ["남성", "여성"], horizontal=True)
        know_time = st.checkbox("태어난 시각을 알아요", value=False)
        hour_val, min_val = None, 0
        if know_time:
            hc1, hc2 = st.columns(2)
            hour_val = hc1.number_input("시 (0~23)", min_value=0, max_value=23, value=12)
            min_val = hc2.number_input("분 (0~59)", min_value=0, max_value=59, value=0)
            st.caption("※ 진태양시(한국 −약32분) 자동 보정됩니다.")
    if st.button("원국 설정 / 변경", type="primary", use_container_width=True):
        h = int(hour_val) if know_time else None
        gender = 1 if gender_label == "남성" else 0
        if cal_type == "음력":
            bd_solar = agent.solar_from_lunar(bd.year, bd.month, bd.day, leap=False)
        elif cal_type == "음력(윤달)":
            bd_solar = agent.solar_from_lunar(bd.year, bd.month, bd.day, leap=True)
        else:
            bd_solar = bd
        p = agent.pillars(bd_solar, h, int(min_val), gender=gender)
        st.session_state.profile = {"ganji": p["day"], "ilgan": p["day"][0],
                                    "ilji": p["day"][1], "year_pillar": p["year"],
                                    "hour_pillar": p.get("hour"),
                                    "gender": "남성" if gender == 1 else "여성",
                                    "daeun_current": p.get("daeun_current"),
                                    "daeun_list": p.get("daeun_list"),
                                    "daeun_forward": p.get("daeun_forward"),
                                    "birth_year": bd_solar.year,
                                    "age": p.get("age"),
                                    "strength": p.get("strength"),
                                    "_birth": (bd_solar.year, bd_solar.month, bd_solar.day,
                                               h, int(min_val))}
        for k in ("chat","messages","mode","category","report"):
            st.session_state.pop(k, None)
        st.rerun()
    if "profile" in st.session_state:
        pr = st.session_state.profile
        line = f"✅ 원국: 일주 **{pr['ganji']}** (일간 {pr['ilgan']}) · {pr.get('gender','')}"
        if pr.get("hour_pillar"):
            line += f" · 시주 {pr['hour_pillar']}"
        st.success(line)
st.write("")
st.write("")

if not os.environ.get("GEMINI_API_KEY"):
    st.error("GEMINI_API_KEY가 없습니다. 설정을 확인해 주세요.")
    st.stop()

CATS = {
    "🔮 종합": "overview",
    "📅 택일": "taegil", "🕰 시기운": "timing", "🧭 적성": "career",
    "🩺 건강운": "health", "🪞 성격": "personality", "💞 궁합": "compatibility",
    "🐶 반려동물": "pet",
}
PURPOSES = list(agent.PURPOSE_RULES.keys())
_has_profile = "profile" in st.session_state
if _has_profile:
    agent.set_profile(st.session_state.profile)

# ══════════ 메인 카드 화면 (항상 유지) ══════════
if "mode" not in st.session_state:
    if not _has_profile:
        st.markdown("<div style='padding:10px 14px;border-radius:12px;margin-bottom:6px;"
                    "background:rgba(197,160,94,0.10);border:1px solid rgba(197,160,94,0.30);"
                    "color:#E8C874;font-size:0.9rem'>👆 먼저 위에서 생년월일·성별을 입력하고 "
                    "<b>원국 설정</b>을 눌러주세요.</div>",
                    unsafe_allow_html=True)
    else:
        pr = st.session_state.profile
        st.markdown(f"<div style='color:#C5A05E;font-size:0.9rem;margin-bottom:6px'>"
                    f"원국 <b>{pr['ganji']}</b> · {pr.get('gender','')} 님, 무엇을 볼까요?</div>",
                    unsafe_allow_html=True)

    # 🔮 종합 사주풀이 — 대표(미끼) 상품, 맨 위에 크게
    st.markdown("#### 🔮 종합 사주풀이  <span style='color:#E8C874;font-size:0.85rem'>990원 · 처음이라면 추천!</span>",
                unsafe_allow_html=True)
    ov_img = load_card_image("overview")
    ov_html = (f"<img class='cc-img' src='{ov_img}'/>" if ov_img
               else "<div class='cc-img' style='display:flex;align-items:center;"
                    "justify-content:center;color:#5B6472;font-size:1.6rem'>🔮</div>")
    st.markdown(
        f"<div class='cat-card'>{ov_html}<div class='cc-body'>"
        f"<div class='cc-top'><span class='cc-title'>🔮 내 사주 종합풀이</span>"
        f"<span class='cc-price'>990원</span></div>"
        f"<div class='cc-desc'>성격·재물·연애·직업·건강·올해운을 한 번에! "
        f"내 사주 전체를 훑어보는 맛보기 종합 리포트예요.</div></div></div>",
        unsafe_allow_html=True)
    if st.button("🔮 종합 사주풀이 보기 →", key="cat_overview", use_container_width=True):
        if not _has_profile:
            st.warning("먼저 위에서 원국을 설정해 주세요.")
        else:
            st.session_state.mode = "report"; st.session_state.preset_cat = "overview"; st.rerun()

    st.markdown("#### 📋 주제별 심화 사주풀이  <span style='color:#E8C874;font-size:0.85rem'>990원 / 1회 · 더 자세히</span>",
                unsafe_allow_html=True)
    cards = [
        ("📅 길일 택일", "이사·시험·계약·개업 등 좋은 날짜 추천", "taegil"),
        ("🕰 시기운 진단", "대운·세운으로 앞으로 유리한 시기 분석", "timing"),
        ("🧭 타고난 적성", "성향과 잘 맞는 진로", "career"),
        ("🩺 건강운·체질", "오행 균형으로 보는 약한 장부", "health"),
        ("🪞 성격·기질", "타고난 성격과 강점", "personality"),
        ("💞 궁합", "두 사람 사주로 보는 인연", "compatibility"),
        ("🐶 반려동물 사주", "우리 아이 성격·건강·집사궁합 (재미로!)", "pet"),
    ]
    cols = st.columns(2)
    for i,(t,d,cat) in enumerate(cards):
        with cols[i%2]:
            img = load_card_image(cat)
            img_html = (f"<img class='cc-img' src='{img}'/>" if img
                        else "<div class='cc-img' style='display:flex;align-items:center;"
                             "justify-content:center;color:#5B6472;font-size:1.6rem'>🐶</div>")
            st.markdown(
                f"<div class='cat-card'>{img_html}<div class='cc-body'>"
                f"<div class='cc-top'><span class='cc-title'>{t}</span>"
                f"<span class='cc-price'>990원</span></div>"
                f"<div class='cc-desc'>{d}</div></div></div>",
                unsafe_allow_html=True)
            clicked = st.button(f"{t} 보기 →", key=f"cat_{cat}", use_container_width=True)
            if clicked:
                if not _has_profile:
                    st.warning("먼저 위에서 원국을 설정해 주세요.")
                else:
                    st.session_state.mode = "report"
                    st.session_state.preset_cat = cat
                    st.rerun()

    st.markdown("---")
    st.markdown("#### 💬 대화형 사주풀이  <span style='color:#E8C874;font-size:0.85rem'>9,900원 · 질문 15회</span>",
                unsafe_allow_html=True)
    st.markdown("<div class='qcard'><div class='d'>동인과 대화하듯 이어서 여쭤보는 상담이에요. "
                "여러 주제를 넘나들며 궁금한 점을 질문 15회까지 깊이 있게 풀어드립니다.</div></div>",
                unsafe_allow_html=True)
    if st.button("💬 대화형 사주풀이 시작  ·  9,900원", key="start_chat",
                 type="primary", use_container_width=True):
        if not _has_profile:
            st.warning("먼저 위에서 원국을 설정해 주세요.")
        else:
            st.session_state.mode = "chat"; st.rerun()

    st.markdown("---")
    st.markdown("#### 🧧 동인 직접 상담  <span style='color:#E8C874;font-size:0.85rem'>50,000원 · 50분</span>",
                unsafe_allow_html=True)
    st.markdown("<div class='qcard' style='border-color:rgba(197,160,94,0.35)'>"
                "<div style='color:#E8C874;font-weight:700;margin-bottom:4px'>사람이 직접 봐드립니다</div>"
                "<div class='d'>AI로 부족하셨다면, 실제 사주 경력자 <b>동인</b>이 1:1로 정성껏 봐드려요. "
                "사주 종합 풀이 + 심층 질문 2개, 50분간 진행됩니다. 예약 후 진행돼요.</div></div>",
                unsafe_allow_html=True)
    if st.button("🧧 동인 직접 상담 예약하기  ·  50,000원", key="start_human",
                 use_container_width=True):
        if not _has_profile:
            st.warning("먼저 위에서 원국을 설정해 주세요.")
        else:
            st.session_state.mode = "human"; st.rerun()
    st.stop()

# 상단 뒤로가기
def _go_home():
    # 원국(profile)·원국관련 정보는 유지, 진행 상태만 초기화
    for k in ("mode","category","report","chat","messages","preset_cat","q_used","booked"):
        st.session_state.pop(k, None)

if st.button("← 처음으로", key="back"):
    _go_home()
    st.rerun()

# ══════════ 모드 1: 카테고리 리포트 (990원) ══════════
if st.session_state.mode == "report":
    st.markdown("### 📋 카테고리 사주풀이  <span style='color:#E8C874;font-size:0.9rem'>990원 / 1회</span>",
                unsafe_allow_html=True)
    _labels = list(CATS.keys())
    _preset = st.session_state.get("preset_cat")
    _idx = next((i for i,(k,v) in enumerate(CATS.items()) if v==_preset), 0)
    cat_label = st.selectbox("어떤 사주를 보고 싶으신가요?", _labels, index=_idx)
    cat = CATS[cat_label]
    form = {}
    st.markdown("<div style='color:#94A3B8;font-size:0.86rem;margin:6px 0'>"
                "아래 항목만 채우시면 됩니다. 잘 모르는 칸은 비워두셔도 알아서 봐드려요.</div>",
                unsafe_allow_html=True)

    if cat == "taegil":
        form["purpose"] = st.selectbox("무슨 일의 날짜를 잡을까요?", PURPOSES)
        colA, colB = st.columns(2)
        y = colA.number_input("연도", min_value=datetime.date.today().year,
                              max_value=datetime.date.today().year+3,
                              value=datetime.date.today().year)
        m = colB.selectbox("월", list(range(1,13)), index=datetime.date.today().month-1)
        import calendar as _cal
        last = _cal.monthrange(int(y), int(m))[1]
        form["date_start"] = f"{int(y)}-{int(m):02d}-01"
        form["date_end"] = f"{int(y)}-{int(m):02d}-{last:02d}"
        st.caption(f"→ {int(y)}년 {int(m)}월 안에서 좋은 날을 찾아드립니다.")
    elif cat == "timing":
        form["purpose"] = st.selectbox("어떤 일의 시기를 볼까요?", PURPOSES)
        form["years"] = st.slider("앞으로 몇 년을 볼까요?", 1, 10, 5)
    elif cat == "compatibility":
        st.markdown("**상대방 정보**")
        colA, colB, colC = st.columns(3)
        form["py"] = colA.number_input("연", min_value=1930, max_value=datetime.date.today().year, value=1992)
        form["pm"] = colB.number_input("월", min_value=1, max_value=12, value=1)
        form["pd"] = colC.number_input("일", min_value=1, max_value=31, value=1)
        colD, colE = st.columns(2)
        form["pg"] = colD.radio("상대 성별", ["여성","남성"], horizontal=True)
        pk = colE.checkbox("상대 시간 알아요")
        form["ph"] = st.number_input("상대 태어난 시(0~23)", 0, 23, 12) if pk else -1
        form["plunar"] = st.checkbox("상대 생일이 음력")
    elif cat == "pet":
        st.markdown("🐶 <b>반려동물 정보</b>  <span style='color:#94A3B8;font-size:0.82rem'>재미로 보는 콘텐츠예요!</span>",
                    unsafe_allow_html=True)
        form["pname"] = st.text_input("반려동물 이름", placeholder="예: 초코")
        colA, colB, colC = st.columns(3)
        form["py"] = colA.number_input("태어난 연", min_value=2000, max_value=datetime.date.today().year, value=2020)
        form["pm"] = colB.number_input("월", min_value=1, max_value=12, value=1)
        form["pd"] = colC.number_input("일", min_value=1, max_value=31, value=1)
        pk = st.checkbox("태어난 시간을 알아요 (모르면 비워두세요)")
        form["ph"] = st.number_input("태어난 시(0~23)", 0, 23, 12) if pk else -1
        form["plunar"] = st.checkbox("생일이 음력이에요")
        if not form.get("pname"):
            form["pname"] = "우리 아이"
        st.caption("※ 집사(주인)와의 궁합은 위에서 설정한 내 원국과 비교해 봐드려요.")
    else:
        st.info("이 항목은 이미 입력하신 사주 정보만으로 풀이해 드려요. 바로 진행하세요.")

    st.write("")
    if st.button(f"🔮 사주 보기  ·  990원", type="primary", use_container_width=True):
        with st.spinner("동인이 사주를 정성껏 풀이하고 있어요…"):
            try:
                st.session_state.report = agent.generate_report(cat, form)
            except Exception as e:
                st.session_state.report = f"죄송해요, 문제가 생겼어요. 잠시 후 다시 시도해 주세요.\n\n`{e}`"
    if st.session_state.get("report"):
        st.markdown("---")
        st.markdown(st.session_state.report)
        st.markdown("---")
        # 📄 PDF 저장
        import os as _os
        _dosa = _os.path.join("images", f"dosa_{cat}.png")
        _title = f"내 사주 {cat_label.split(' ',1)[-1] if ' ' in cat_label else cat_label}풀이"
        try:
            _pdf = make_report_pdf(_title, st.session_state.report,
                                   dosa_img=_dosa if _os.path.exists(_dosa) else None)
        except Exception:
            _pdf = None
        if _pdf:
            st.download_button("📄 PDF로 저장하기", data=_pdf,
                               file_name="동인_사주풀이.pdf", mime="application/pdf",
                               use_container_width=True)
        st.markdown("<div style='padding:12px 16px;border-radius:12px;margin-top:8px;"
                    "background:rgba(158,43,37,0.12);border:1px solid rgba(197,160,94,0.35)'>"
                    "💬 더 깊이, 이어서 물어보고 싶으신가요?<br>"
                    "<b>대화형 사주풀이(9,900원 · 질문 15회)</b>에서 대화하듯 이어갈 수 있어요.</div>",
                    unsafe_allow_html=True)
        if st.button("대화형 사주풀이로 이어가기", use_container_width=True):
            for k in ("mode","report"): st.session_state.pop(k, None)
            st.session_state.mode = "chat"; st.rerun()

# ══════════ 모드 2: 대화형 사주풀이 (9,900원 · 15회) ══════════
elif st.session_state.mode == "chat":
    LIMIT = 15
    used = st.session_state.get("q_used", 0)
    remain = LIMIT - used
    st.markdown(f"### 💬 대화형 사주풀이  "
                f"<span style='color:#E8C874;font-size:0.9rem'>남은 질문 {remain}회</span>",
                unsafe_allow_html=True)
    if "chat" not in st.session_state:
        try:
            st.session_state.gemini_client, st.session_state.chat = agent.new_chat()
        except Exception as e:
            st.error(f"대화 세션 생성 실패: {e}"); st.stop()
        st.session_state.q_used = 0; remain = LIMIT
        st.session_state.messages = [{"role":"assistant",
            "content":"안녕하세요, 동인입니다. 🀄 무엇이든 편하게 여쭤보세요.\n\n"
                      "📅 \"10월에 이사 좋은 날?\"  ·  🕰 \"내년에 이직해도 될까?\"\n"
                      "🧭 \"내 적성이 뭐야?\"  ·  🩺 \"건강운 봐줘\"\n"
                      "🪞 \"나는 어떤 사람이야?\"  ·  💞 \"○○년생이랑 궁합 어때?\""}]
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    if remain <= 0:
        st.info("질문 15회를 모두 사용하셨어요. 더 깊은 상담이 필요하시면 "
                "**🧧 동인 직접 상담(50,000원)**을 이용해 보세요.")
        if st.button("🧧 동인 직접 상담 예약하기", use_container_width=True):
            for k in ("mode","chat","messages","q_used"): st.session_state.pop(k, None)
            st.session_state.mode = "human"; st.rerun()
    else:
        q = st.chat_input(f"편하게 말씀하세요 (남은 질문 {remain}회)")
        if q:
            st.session_state.messages.append({"role":"user","content":q})
            with st.chat_message("user"): st.markdown(q)
            with st.chat_message("assistant"):
                with st.spinner("생각하는 중…"):
                    try:
                        text = agent.reply(st.session_state.chat, q)
                    except Exception as e:
                        text = f"죄송해요, 문제가 생겼어요. 잠시 후 다시 시도해 주세요.\n\n`{e}`"
                st.markdown(text)
            st.session_state.messages.append({"role":"assistant","content":text})
            st.session_state.q_used = used + 1
            st.rerun()

# ══════════ 모드 3: 동인 직접 상담 예약 (50,000원) ══════════
elif st.session_state.mode == "human":
    st.markdown("### 🧧 동인 직접 상담 예약  <span style='color:#E8C874;font-size:0.9rem'>50,000원 · 50분</span>",
                unsafe_allow_html=True)
    st.markdown("<div class='qcard'><div class='d'>실제 사주 경력자 <b>동인</b>이 1:1로 봐드립니다.<br>"
                "· 사주 종합 풀이 + 심층 질문 2개<br>· 진행 시간 50분<br>· 예약 확정 후 안내드려요</div></div>",
                unsafe_allow_html=True)
    st.write("")
    pr = st.session_state.profile
    # 왼쪽에서 설정한 사주 정보를 예약에 자동 포함
    _birth = pr.get("_birth")
    birth_str = "미입력"
    if _birth:
        y,m,d,hh,mi = _birth
        birth_str = f"{y}년 {m}월 {d}일" + (f" {hh:02d}:{mi:02d}" if hh is not None else " (시간 미입력)")
    st.markdown("<div class='qcard' style='border-color:rgba(197,160,94,0.35)'>"
                "<div style='color:#E8C874;font-weight:700;margin-bottom:4px'>📌 상담에 전달될 내 사주 정보</div>"
                f"<div class='d'>· 생년월일: {birth_str} · {pr.get('gender','')}<br>"
                f"· 원국: 일주 {pr.get('ganji','')} (일간 {pr.get('ilgan','')})"
                + (f" · 시주 {pr.get('hour_pillar')}" if pr.get('hour_pillar') else "")
                + "<br><span style='color:#94A3B8;font-size:0.82rem'>위 ‘원국 설정’에서 입력한 정보가 동인에게 함께 전달됩니다. "
                  "잘못됐다면 위에서 다시 설정해 주세요.</span></div></div>",
                unsafe_allow_html=True)
    if not st.session_state.get("booked"):
        with st.form("booking"):
            st.markdown("**예약 정보를 입력해 주세요**")
            name = st.text_input("성함", placeholder="예: 홍길동")
            phone = st.text_input("연락처", placeholder="예: 010-1234-5678")
            c1, c2 = st.columns(2)
            pref_date = c1.date_input("희망 날짜", value=datetime.date.today()+datetime.timedelta(days=2),
                                      min_value=datetime.date.today())
            pref_time = c2.selectbox("희망 시간", [f"{h}:00" for h in range(10, 22)])
            memo = st.text_area("미리 남기실 질문/메모 (선택)",
                placeholder="예시)\n"
                            "· 무엇이 궁금하신가요? (예: 올해 이직운, 결혼 시기, 사업 방향 등)\n"
                            "· 심층 질문 2가지를 미리 정리해 주시면 상담이 더 깊어집니다.\n"
                            "· 특별히 걱정되거나 상황이 있다면 자유롭게 적어주세요.\n"
                            "  (예: 3년째 이직을 고민 중이고, 지금 자리가 맞는지 알고 싶어요)",
                height=140)
            submitted = st.form_submit_button("예약 신청하고 결제하기 · 50,000원",
                                              type="primary", use_container_width=True)
        if submitted:
            if not name or not phone:
                st.warning("성함과 연락처를 입력해 주세요.")
            else:
                booking = {"name":name,"phone":phone,
                    "date":str(pref_date),"time":pref_time,"memo":memo,
                    "birth":birth_str,"gender":pr.get('gender',''),
                    "ganji":pr.get('ganji',''),"ilgan":pr.get('ilgan',''),
                    "hour_pillar":pr.get('hour_pillar','')}
                with st.spinner("예약을 접수하는 중…"):
                    booking["_sent"] = send_booking_to_sheet(booking)
                st.session_state.booked = booking
                st.rerun()
    else:
        b = st.session_state.booked
        if b.get("_sent"):
            st.success("예약 신청이 접수되었습니다! 🎉")
        else:
            st.warning("예약이 화면에는 접수됐지만, 서버 전송에 실패했을 수 있어요. "
                       "확실히 하시려면 입력하신 연락처로 문의 부탁드립니다.")
        st.markdown(f"- 성함: {b['name']}\n- 연락처: {b['phone']}\n"
                    f"- 희망 일시: {b['date']} · {b['time']}\n"
                    f"- 사주 정보: {b.get('birth','')} · {b.get('gender','')} "
                    f"(일주 {b.get('ganji','')})")
        if b.get("memo"):
            st.markdown(f"- 남기신 질문/메모:\n\n> {b['memo']}")
        st.markdown("<div style='padding:12px 16px;border-radius:12px;margin-top:8px;"
                    "background:rgba(158,43,37,0.12);border:1px solid rgba(197,160,94,0.35)'>"
                    "💳 결제 안내와 최종 일정은 입력하신 연락처로 개별 안내드립니다.<br>"
                    "<span style='color:#94A3B8;font-size:0.85rem'>(결제 시스템은 곧 연동될 예정입니다.)</span></div>",
                    unsafe_allow_html=True)
