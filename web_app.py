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

st.set_page_config(page_title="동인 — AI 사주 상담", page_icon="🀄", layout="wide",
                   initial_sidebar_state="expanded")

# ---------- 커스텀 테마 (Deep Midnight Navy + Gold + Glass) ----------
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

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

/* 텍스트 대비 강제 (모바일에서 글자가 배경에 묻히는 문제 해결) */
.stApp, .stApp p, .stApp span, .stApp label, .stApp li, .stApp div {
  color:#E2E8F0;
}
.stMarkdown, [data-testid="stChatMessage"] * { color:#E9EEF7 !important; }
label, .stCheckbox label, .stNumberInput label, .stDateInput label { color:#CBD5E1 !important; }
h1,h2,h3,h4,h5 { color:#F1F5F9; }
/* 위젯 내부 값 텍스트도 밝게 */
.stNumberInput input, .stDateInput input, .stSelectbox div { color:#E2E8F0 !important; }

/* 모바일 전용 보정 */
@media (max-width: 768px) {
  /* 사이드바 열림 버튼을 눈에 띄게 */
  [data-testid="stSidebarCollapsedControl"] {
    background:linear-gradient(135deg,#9E2B25,#7A1E1E) !important;
    border-radius:10px !important; padding:4px !important;
  }
  [data-testid="stSidebarCollapsedControl"] svg { color:#fff !important; }
  /* 본문 글자 살짝 키워 가독성 */
  .stApp p, .stApp li { font-size:0.98rem; line-height:1.6; }
  h1 { font-size:1.5rem !important; }
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 棟寅 · 사주 원국 설정")
    st.markdown("<span style='color:#94A3B8;font-size:0.85rem'>정밀한 분석을 위해 "
                "대상자의 사주 정보를 입력하세요.</span>", unsafe_allow_html=True)
    st.write("")
    today = datetime.date.today()
    cal_type = st.radio("달력", ["양력", "음력", "음력(윤달)"], horizontal=True)
    bd = st.date_input("생년월일", value=datetime.date(1990, 1, 1),
                       min_value=datetime.date(1930, 1, 1), max_value=today,
                       format="YYYY-MM-DD")
    if cal_type != "양력":
        st.caption("※ 입력한 날짜를 음력으로 보고 양력으로 자동 변환합니다.")
    gender_label = st.radio("성별", ["남성", "여성"], horizontal=True)
    know_time = st.checkbox("태어난 시각을 알아요", value=False)
    hour_val, min_val = None, 0
    if know_time:
        c1, c2 = st.columns(2)
        hour_val = c1.number_input("시 (0~23)", min_value=0, max_value=23, value=12)
        min_val = c2.number_input("분 (0~59)", min_value=0, max_value=59, value=0)
        st.caption("※ 진태양시(한국 −약32분) 자동 보정됩니다.")
    if st.button("원국 설정 / 새 상담 시작", type="primary", use_container_width=True):
        h = int(hour_val) if know_time else None
        gender = 1 if gender_label == "남성" else 0
        # 음력이면 양력으로 변환
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
                                    "strength": p.get("strength")}
        agent.set_profile(st.session_state.profile)
        try:
            st.session_state.gemini_client, st.session_state.chat = agent.new_chat()
            st.session_state.messages = [{"role": "assistant",
                "content": "안녕하세요, 동인입니다. 🀄\n\n좋은 날짜를 잡는 택일, 지금·앞으로의 시기운, "
                           "타고난 적성까지 편하게 여쭤보세요. 예를 들어 \"10월에 이사 좋은 날?\", "
                           "\"내년에 이직해도 될까?\", \"내 적성이 뭐야?\"처럼요."}]
        except Exception as e:
            st.session_state.chat = None
            st.session_state.messages = []
            st.error(f"대화 세션 생성 실패: {e}")

    if "profile" in st.session_state:
        pr = st.session_state.profile
        line = f"원국: 일주 **{pr['ganji']}** (일간 {pr['ilgan']}) · {pr.get('gender','')}"
        if pr.get("hour_pillar"):
            line += f"\n\n시주: {pr['hour_pillar']}"
        cur = pr.get("daeun_current")
        if cur:
            line += f"\n\n현재 대운: {cur['ganzhi']} ({cur['start']}~{cur['end']}세)"
        stg = pr.get("strength")
        if stg:
            yong = "·".join(stg.get("용신방향", []))
            line += f"\n\n{stg.get('판정','')} · 용신 {yong}"
        st.success(line)
    st.divider()
    chips = "".join(f"<span class='chip'>{p}</span>" for p in agent.PURPOSE_RULES.keys())
    st.markdown("<div style='color:#94A3B8;font-size:0.8rem;margin-bottom:6px'>지원 상담 도메인</div>"
                + chips, unsafe_allow_html=True)

st.markdown("<div style='display:flex;align-items:center;gap:12px'>"
            "<span style='display:inline-flex;align-items:center;justify-content:center;"
            "width:46px;height:46px;border-radius:8px;background:linear-gradient(135deg,#9E2B25,#7A1E1E);"
            "border:1px solid rgba(232,200,116,0.7);color:#F5E6C8;font-weight:800;font-size:0.95rem;"
            "line-height:1.0;letter-spacing:-1px'>棟寅</span>"
            "<h1 style='margin:0'>동인 · AI 사주 상담</h1></div>", unsafe_allow_html=True)
st.markdown("<span style='color:#C5A05E;font-size:0.82rem'>● 명리 정밀 엔진 · 택일 · 시기운 · 적성</span>",
            unsafe_allow_html=True)
st.write("")

if not os.environ.get("GEMINI_API_KEY"):
    st.error("GEMINI_API_KEY가 없습니다. API_KEY.env 파일을 확인하고 이 폴더에서 실행했는지 보세요.")
elif "chat" not in st.session_state:
    st.markdown("#### 생년월일을 입력하면, 날짜 · 시기운 · 적성을 함께 봐드립니다")
    st.markdown("<span style='color:#94A3B8'>왼쪽에서 생년월일과 성별을 입력하고 "
                "<b>원국 설정 / 새 상담 시작</b>을 누르면 상담이 시작됩니다.</span>",
                unsafe_allow_html=True)
    st.markdown("<div style='margin-top:8px;padding:10px 14px;border-radius:12px;"
                "background:rgba(197,160,94,0.10);border:1px solid rgba(197,160,94,0.30);"
                "color:#E8C874;font-size:0.88rem'>📱 휴대폰에서는 왼쪽 위 <b>‹ 화살표</b>를 "
                "눌러 사주 입력창을 여세요.</div>", unsafe_allow_html=True)
    st.write("")
    cards = [
        ("📅 길일 택일", "이사·시험·계약·개업 등 좋은 날짜를 콕 집어 추천"),
        ("🕰 시기운 진단", "지금·앞으로 몇 년 중 언제가 유리한지 대운·세운으로 분석"),
        ("🧭 타고난 적성", "일간·일주로 보는 성향과 잘 맞는 진로·직업"),
        ("💬 편하게 대화", "\"내년에 이직해도 될까?\"처럼 말하듯 물어보세요"),
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
