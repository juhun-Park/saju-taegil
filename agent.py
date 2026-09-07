# -*- coding: utf-8 -*-
"""대화형 택일 에이전트 — 제미나이가 대화를 이끌고, 계산이 필요하면 엔진을 도구로 호출.
필요: pip install google-genai lunar_python python-dotenv"""
import os, datetime, logging, warnings
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google.genai").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")
try:
    from dotenv import load_dotenv
    load_dotenv("API_KEY.env"); load_dotenv()
except ImportError:
    pass
from taegil_engine import pillars, score_day, PURPOSE_RULES

MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")

SIPSIN_MEANING={'정관':'명예·합격·인정','편관':'권위·결단·경쟁','정인':'문서·시험·자격·후원',
 '편인':'전문·기술·직관','식신':'표현·안정·수완','상관':'관을 극함(시험·관운 방해)',
 '정재':'착실한 결실·신용','편재':'유통·수완·변동재','비견':'주체·동료','겁재':'경쟁·손재'}
SINSAL_MEANING={'장성':'중심·리더십','반안':'안정적 상승·승진','역마':'이동·확장','화개':'학문·예술',
 '육해':'지체·꼼꼼함','겁살':'돌발','재살':'다툼','천살':'변수','년살':'구설','망신':'노출','지살':'시작','월살':'위축'}

# 도구가 참조할 현재 사용자 원국 (폼에서 설정)
_PROFILE = {}
def set_profile(p): 
    global _PROFILE; _PROFILE = p

def _to_date(v, default):
    try: return datetime.date.fromisoformat(str(v)[:10])
    except Exception: return default

# ---------- 제미나이가 호출할 '도구' ----------
def run_taegil(purpose: str, date_start: str, date_end: str) -> dict:
    """등록된 사용자의 사주(원국)를 기준으로, 주어진 기간에서 목적에 좋은 날짜를 계산해 돌려준다.
    날짜의 간지·십신·신살·길흉은 이 함수가 정확히 계산하므로, 모델은 절대 스스로 날짜 길흉을 지어내지 말고
    이 함수의 결과만 사용해 설명해야 한다.
    Args:
        purpose: 택일 목적. 반드시 다음 중 하나: '합격/시험/지원', '이사/이동', '이직/취업',
                 '개업/창업', '계약/거래', '혼인/결혼'.
        date_start: 검색 시작일 'YYYY-MM-DD'.
        date_end: 검색 종료일 'YYYY-MM-DD'.
    Returns:
        top_days(추천 상위일)와 avoid_days(피할 날) 목록. 각 항목은 날짜·간지·십신·신살·길흉·근거 포함.
        지원하지 않는 목적이면 error를 돌려준다.
    """
    if purpose not in PURPOSE_RULES:
        return {"error": f"'{purpose}'은(는) 아직 지원하지 않는 목적입니다. "
                         f"지원 목적: {list(PURPOSE_RULES.keys())}"}
    if not _PROFILE:
        return {"error": "사용자 사주가 아직 등록되지 않았습니다. 생년월일을 먼저 입력받아야 합니다."}
    il, ji = _PROFILE['ilgan'], _PROFILE['ilji']
    today = datetime.date.today()
    s = _to_date(date_start, today); e = _to_date(date_end, today+datetime.timedelta(days=90))
    if e < s: s, e = today, today+datetime.timedelta(days=90)
    days = min((e-s).days+1, 120)
    res = [score_day(s+datetime.timedelta(days=i), il, ji, purpose) for i in range(days)]
    res.sort(key=lambda x: -x['score'])
    def pack(r):
        ss = ' / '.join(f"{x}({SIPSIN_MEANING.get(x,'')})" for x in r['십신'].split('/'))
        return {"날짜": r['date'], "간지": r['day_pillar'],
                "십신": ss, "신살": f"{r['신살']}({SINSAL_MEANING.get(r['신살'],'')})",
                "길흉일": ('길일(황도)' if r['황흑도']=='吉' else '흉일(흑도)' if r['황흑도']=='凶' else '보통'),
                "손없는날": r['손없는날'], "점수": r['score']}
    return {"purpose": purpose, "기간": f"{s} ~ {e}",
            "top_days": [pack(r) for r in res[:3]],
            "avoid_days": [pack(r) for r in res[-2:]]}



# ---------- 커리어(원국 직업 적성) 조회 ----------
import json as _json
_CAREER=None
def _load_career():
    global _CAREER
    if _CAREER is None:
        try:
            with open("career_ruleDB.json", encoding="utf-8") as f:
                _CAREER=_json.load(f)
        except Exception:
            _CAREER={}
    return _CAREER

def run_career() -> dict:
    """등록된 사용자의 사주(원국)를 기준으로 타고난 직업 적성·성향을 조회한다.
    '내 직업 적성', '어떤 일이 맞나', '이직/진로 방향', '나는 사업가형인가' 같은
    '타고난 성향' 질문에 사용한다. (특정 날짜를 잡는 택일이 아니라 원국 해석용)
    간지·일간별 직업 데이터는 이 함수가 정확히 돌려주므로, 모델은 결과만 근거로 설명해야 한다.
    Returns:
        일간·일주(60갑자) 기반 직업 적성, 성향 특성, 관련 십신.
    """
    if not _PROFILE:
        return {"error": "사용자 사주가 아직 등록되지 않았습니다."}
    db=_load_career()
    if not db: return {"error":"커리어 데이터를 불러오지 못했습니다."}
    il=_PROFILE['ilgan']; gj=_PROFILE['ganji']
    L=db['layers']
    ilgan_rec=next((r for r in L['ilgan']['records'] if r['key']['ilgan']==il), None)
    ganji_rec=next((r for r in L['ganji']['records'] if r['key']['ganji']==gj), None)
    oh=ilgan_rec['key']['ohaeng'] if ilgan_rec else None
    ohaeng_rec=next((r for r in L['ohaeng']['records'] if r['key']['ohaeng']==oh), None)
    out={"일간":il, "일주":gj}
    if ilgan_rec:
        out["일간_본성"]=ilgan_rec.get('core_nature','')
        out["일간_직업군"]=ilgan_rec.get('career_types',[])
    if ganji_rec:
        out["일주_특성"]=ganji_rec.get('characteristic','')
        out["일주_직업적성"]=ganji_rec.get('career_aptitude',[])
    if ohaeng_rec:
        out["오행_적합직업"]=ohaeng_rec.get('suited_jobs',[])
    return out

SYSTEM = None
def _system():
    today = datetime.date.today().isoformat()
    supported = ", ".join(PURPOSE_RULES.keys())
    return f"""당신은 20년 경력의 따뜻하고 신뢰감 있는 명리학 택일(擇日) 전문 상담사입니다. 오늘은 {today}입니다.

[역할과 태도]
- 손님을 편안하게 대하는 진짜 상담사처럼 대화합니다. 기계적인 안내가 아니라, 공감하고 배려하는 말투를 씁니다.
- 사용자의 사주(원국)는 이미 시스템에 등록되어 있습니다. 생년월일을 다시 묻지 마세요.

[정보 수집 — 대화로 자연스럽게]
- 택일을 하려면 (1)목적 (2)대략의 시기가 필요합니다.
- 정보가 빠져 있으면 딱딱하게 나열하지 말고, 공감을 곁들여 하나씩 자연스럽게 물어보세요.
  예) "이사를 준비하시는군요! 설레기도 하고 신경 쓸 것도 많으시죠. 혹시 언제쯤 옮기실 생각이신가요?"
- 시기가 막연하면("곧", "가을쯤") 그대로 도구에 넉넉한 기간으로 넘겨도 됩니다.

[두 종류의 질문 — 도구를 구분해 사용]
- (가) 택일 질문 = 특정 일을 '언제 하면 좋은지'(이사·시험·이직 날짜 등). → 목적과 시기가 파악되면 run_taegil 호출.
- (나) 적성 질문 = '타고난 직업 성향/진로 방향'(내 적성, 어떤 일이 맞나, 사업가형인지 등). → 시기가 필요 없고, run_career 호출.
- 사용자의 말이 '언제'에 관한 것이면 (가), '무엇/어떤 성향'에 관한 것이면 (나)로 판단하세요. 애매하면 무엇을 원하는지 한 번 물어보세요.
- 절대 스스로 간지·십신·신살·길흉·적성을 지어내지 마세요. 오직 도구가 돌려준 데이터만 근거로 씁니다.

[답변 구성 — 구체적·풍부·명확하게]
도구 결과를 받으면 다음 구조로, 넉넉하고 정성껏 설명하세요:
1) 공감 한마디로 시작 (1문장).
2) 가장 추천하는 날 2개: 각 날짜마다 ▸왜 좋은지(그 날의 십신·신살이 이 목적에 어떻게 작용하는지) ▸명리 용어는 반드시 괄호로 쉬운 뜻을 달아 초보자도 이해하게 ▸그 날을 실제로 어떻게 활용하면 좋은지 실천 팁까지. 날짜당 3~4문장 이상 충분히.
3) 피하면 좋은 날 1개와 그 이유를 쉽게.
4) 마지막에 "💡 한 줄 요약:"으로 핵심 결론.
- 문체는 따뜻한 존댓말. 단정적 예언("반드시 합격") 대신 "유리한 기운", "도움이 되는 흐름"처럼 부드럽게.
- 마크다운 볼드(**)는 쓰지 말고, 날짜는 "10월 8일(乙卯)"처럼 표기하세요.

[지원 범위]
- 현재 지원 목적: {supported}.
- 그 외 목적(수술·제사·여행 등)을 물으면, 아직 준비 중이라 위 목적만 도와드릴 수 있다고 솔직하고 정중하게 안내하고, 지원 가능한 목적을 부드럽게 제안하세요."""

def new_chat():
    """새 대화 세션 생성 (원국 설정 후 호출). (client, chat) 튜플 반환 —
    호출부에서 client를 붙잡아두어야 httpx 연결이 닫히지 않는다."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    chat = client.chats.create(model=MODEL, config=types.GenerateContentConfig(
        system_instruction=_system(), tools=[run_taegil, run_career], temperature=0.7,
        max_output_tokens=2048))  # 답변이 길어도 잘리지 않도록 넉넉히
    return client, chat

def reply(chat, user_text, tries=4):
    """사용자 메시지 전송 → (도구 자동 호출 포함) 최종 답변 텍스트."""
    import time
    from google.genai import errors
    for i in range(tries):
        try:
            return chat.send_message(user_text).text
        except errors.ServerError:
            if i==tries-1: raise
            time.sleep(2*(i+1))

# ---------- 터미널 데모 ----------
if __name__ == "__main__":
    print("="*54); print("  🔮 AI 택일 상담 (대화형)"); print("="*54)
    raw = input("생년월일 (예: 1992-02-13): ").strip()
    y,m,d = [int(x) for x in raw.replace(".","-").replace("/","-").split("-")]
    hr = input("태어난 시 (0~23, 모르면 엔터): ").strip()
    p = pillars(datetime.date(y,m,d), int(hr) if hr else None)
    set_profile({'ganji':p['day'],'ilgan':p['day'][0],'ilji':p['day'][1]})
    print(f"→ 원국 {p['day']} 등록 완료. 편하게 말씀하세요. (엔터로 종료)\n")
    _client, chat = new_chat()
    while True:
        q = input("🙋 ").strip()
        if not q: print("\n상담을 마칩니다. 좋은 날 되세요! 🍀"); break
        print("\n🔮", reply(chat, q), "\n")