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

st.set_page_config(page_title="AI 택일 상담", page_icon="🔮", layout="wide")

# ---------- 커스텀 테마 (Deep Midnight Navy + Gold + Glass) ----------
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

/* 전체 배경 */
.stApp {
  background: radial-gradient(1200px 600px at 80% -10%, rgba(124,58,237,0.10), transparent 60%),
              radial-gradient(1000px 500px at 0% 110%, rgba(245,158,11,0.08), transparent 55%),
              #0B0F19;
  color: #E2E8F0;
  font-family: 'Pretendard','Inter',sans-serif;
}
/* 사이드바 */
section[data-testid="stSidebar"] > div {
  background: rgba(15,23,42,0.72);
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(255,255,255,0.08);
}
h1,h2,h3,h4 { font-family:'Pretendard','Inter',sans-serif; letter-spacing:-0.02em; }
h1 { background:linear-gradient(135deg,#F59E0B,#E5C07B); -webkit-background-clip:text;
     -webkit-text-fill-color:transparent; font-weight:800; }

/* 입력 필드 */
.stDateInput input, .stNumberInput input, .stTextInput input {
  background: rgba(255,255,255,0.04)!important; color:#E2E8F0!important;
  border:1px solid rgba(255,255,255,0.10)!important; border-radius:12px!important;
}
.stDateInput input:focus, .stNumberInput input:focus {
  border-color:#F59E0B!important; box-shadow:0 0 0 3px rgba(245,158,11,0.25)!important;
}

/* 버튼 = 골드 그라디언트 */
.stButton > button {
  background:linear-gradient(135deg,#D97706,#B45309); color:#FFF7ED;
  border:none; border-radius:12px; font-weight:700; padding:0.6rem 1rem;
  transition:all .18s ease;
}
.stButton > button:hover {
  transform:translateY(-2px); color:#fff;
  box-shadow:0 4px 20px rgba(245,158,11,0.35);
}

/* 채팅 말풍선 = 글래스 카드 */
[data-testid="stChatMessage"] {
  background: rgba(255,255,255,0.04); backdrop-filter: blur(10px);
  border:1px solid rgba(255,255,255,0.08); border-radius:16px;
  padding:0.4rem 0.8rem; margin-bottom:0.4rem;
}
/* 성공/정보 박스 */
[data-testid="stAlert"] {
  background: rgba(255,255,255,0.04); border:1px solid rgba(245,158,11,0.25);
  border-radius:14px; color:#E2E8F0;
}
/* 배지 칩 */
.chip { display:inline-block; padding:4px 12px; margin:3px 4px;
  background:rgba(245,158,11,0.10); border:1px solid rgba(245,158,11,0.30);
  color:#E5C07B; border-radius:999px; font-size:0.78rem; }
/* 퀵스타트 카드 */
.qcard { background:rgba(255,255,255,0.04); backdrop-filter:blur(10px);
  border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:18px 18px;
  margin-bottom:14px; transition:all .18s ease; }
.qcard:hover { border-color:rgba(245,158,11,0.45); transform:translateY(-2px);
  box-shadow:0 6px 24px rgba(245,158,11,0.12); }
.qcard .t { color:#F1F5F9; font-weight:700; font-size:1.02rem; margin-bottom:4px; }
.qcard .d { color:#94A3B8; font-size:0.86rem; line-height:1.45; }
.chat-input-hint { color:#64748B; font-size:0.82rem; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 사주 원국 설정")
    st.markdown("<span style='color:#94A3B8;font-size:0.85rem'>정밀한 분석을 위해 "
                "대상자의 사주 정보를 입력하세요.</span>", unsafe_allow_html=True)
    st.write("")
    today = datetime.date.today()
    bd = st.date_input("생년월일", value=datetime.date(1990, 1, 1),
                       min_value=datetime.date(1930, 1, 1), max_value=today,
                       format="YYYY-MM-DD")
    know_time = st.checkbox("태어난 시각을 알아요", value=False)
    hour_val, min_val = None, 0
    if know_time:
        c1, c2 = st.columns(2)
        hour_val = c1.number_input("시 (0~23)", min_value=0, max_value=23, value=12)
        min_val = c2.number_input("분 (0~59)", min_value=0, max_value=59, value=0)
        st.caption("※ 진태양시(한국 −약32분) 자동 보정됩니다.")
    if st.button("원국 설정 / 새 상담 시작", type="primary", use_container_width=True):
        h = int(hour_val) if know_time else None
        p = agent.pillars(bd, h, int(min_val))
        st.session_state.profile = {"ganji": p["day"], "ilgan": p["day"][0],
                                    "ilji": p["day"][1], "year_pillar": p["year"],
                                    "hour_pillar": p.get("hour")}
        agent.set_profile(st.session_state.profile)
        try:
            st.session_state.gemini_client, st.session_state.chat = agent.new_chat()
            st.session_state.messages = [{"role": "assistant",
                "content": "안녕하세요! 택일 상담을 도와드릴게요. 어떤 일의 날짜를 잡고 싶으신가요? "
                           "(예: 이사, 시험·원서 접수 등) 편하게 말씀해 주세요 🙂"}]
        except Exception as e:
            st.session_state.chat = None
            st.session_state.messages = []
            st.error(f"대화 세션 생성 실패: {e}")

    if "profile" in st.session_state:
        pr = st.session_state.profile
        line = f"원국: 일주 **{pr['ganji']}** (일간 {pr['ilgan']})"
        if pr.get("hour_pillar"):
            line += f"\n\n시주: {pr['hour_pillar']}"
        st.success(line)
    st.divider()
    chips = "".join(f"<span class='chip'>{p}</span>" for p in agent.PURPOSE_RULES.keys())
    st.markdown("<div style='color:#94A3B8;font-size:0.8rem;margin-bottom:6px'>지원 상담 도메인</div>"
                + chips, unsafe_allow_html=True)

st.markdown("<div style='display:flex;align-items:center;gap:10px'>"
            "<span style='font-size:1.6rem'>🔮</span>"
            "<h1 style='margin:0'>AI 택일 상담</h1></div>", unsafe_allow_html=True)
st.markdown("<span style='color:#F59E0B;font-size:0.82rem'>● AI 정밀 택일 엔진 활성화됨</span>",
            unsafe_allow_html=True)
st.write("")

if not os.environ.get("GEMINI_API_KEY"):
    st.error("GEMINI_API_KEY가 없습니다. API_KEY.env 파일을 확인하고 이 폴더에서 실행했는지 보세요.")
elif "chat" not in st.session_state:
    st.markdown("#### 사주 원국을 설정하고 맞춤형 길일(吉日)을 확인하세요")
    st.markdown("<span style='color:#94A3B8'>왼쪽에서 생년월일을 입력하고 "
                "<b>원국 설정 / 새 상담 시작</b>을 누르면 상담이 시작됩니다.</span>",
                unsafe_allow_html=True)
    st.write("")
    cards = [
        ("취업 · 이직 · 시험 택일", "면접, 원서 접수, 이직 협상에 유리한 날"),
        ("이사 · 이동 택일", "손 없는 날 및 가택 이동 대길일 분석"),
        ("혼인 · 상견례 택일", "안정과 화합의 기운을 고려한 일정"),
        ("계약 · 창업 · 개업 택일", "재물운과 번영을 극대화하는 날 추천"),
    ]
    cols = st.columns(2)
    for i, (t, d) in enumerate(cards):
        with cols[i % 2]:
            st.markdown(f"<div class='qcard'><div class='t'>{t}</div>"
                        f"<div class='d'>{d}</div></div>", unsafe_allow_html=True)
else:
    agent.set_profile(st.session_state.profile)
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    q = st.chat_input("편하게 말씀하세요")
    if q:
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            with st.spinner("생각하는 중…"):
                try:
                    text = agent.reply(st.session_state.chat, q)
                except Exception as e:
                    text = f"죄송해요, 문제가 생겼어요. 잠시 후 다시 시도해 주세요.\n\n`{e}`"
            st.markdown(text)
        st.session_state.messages.append({"role": "assistant", "content": text})