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
from taegil_engine import pillars, score_day, PURPOSE_RULES, solar_from_lunar

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
    yongsin = (_PROFILE.get('strength') or {}).get('용신방향')
    res = [score_day(s+datetime.timedelta(days=i), il, ji, purpose, yongsin=yongsin) for i in range(days)]
    res.sort(key=lambda x: -x['score'])
    def pack(r):
        ss = ' / '.join(f"{x}({SIPSIN_MEANING.get(x,'')})" for x in r['십신'].split('/'))
        return {"날짜": r['date'], "간지": r['day_pillar'],
                "십신": ss, "신살": f"{r['신살']}({SINSAL_MEANING.get(r['신살'],'')})",
                "길흉일": ('길일(황도)' if r['황흑도']=='吉' else '흉일(흑도)' if r['황흑도']=='凶' else '보통'),
                "손없는날": r['손없는날'], "점수": r['score']}
    st_info = _PROFILE.get('strength') or {}
    return {"purpose": purpose, "기간": f"{s} ~ {e}",
            "신강약": st_info.get('판정'), "용신방향": st_info.get('용신방향'),
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
    if _PROFILE.get("gender"): out["성별"]=_PROFILE["gender"]
    if _PROFILE.get("strength"):
        st=_PROFILE["strength"]
        out["신강약"]=st.get("판정"); out["용신방향"]=st.get("용신방향")
    if _PROFILE.get("daeun_current"):
        c=_PROFILE["daeun_current"]
        out["현재_대운"]=f"{c['ganzhi']} ({c['start']}~{c['end']}세)"
    if ilgan_rec:
        out["일간_본성"]=ilgan_rec.get('core_nature','')
        out["일간_직업군"]=ilgan_rec.get('career_types',[])
    if ganji_rec:
        out["일주_특성"]=ganji_rec.get('characteristic','')
        out["일주_직업적성"]=ganji_rec.get('career_aptitude',[])
    if ohaeng_rec:
        out["오행_적합직업"]=ohaeng_rec.get('suited_jobs',[])
    return out

def run_timing_check(purpose: str, years: int = 5) -> dict:
    """등록된 사용자의 대운(大運)+세운(歲運)을 향후 여러 해에 걸쳐 종합 진단해,
    어느 해가 그 목적에 가장 유리한지 비교한다.
    '지금 이직해도 될까', '앞으로 몇 년 중 언제 창업이 좋을까', '내년 결혼운은',
    '향후 3년 이직 시기' 처럼 '특정 날짜'가 아니라 '어느 시기/어느 해가 좋은지'를
    묻는 질문에 사용한다. 대운이 중간에 바뀌면 그 해 나이에 맞는 대운으로 자동 반영한다.
    12운성 강약과 대운·세운의 십신을 결합해 계산하므로, 모델은 결과만 근거로 설명해야 한다.
    Args:
        purpose: 진단할 목적. 반드시 다음 중 하나: '합격/시험/지원', '이사/이동', '이직/취업',
                 '개업/창업', '계약/거래', '혼인/결혼'.
        years: 비교할 햇수. 사용자가 기간을 말하면 그 값(예: 3, 10), 없으면 기본 5.
    Returns:
        best(가장 유리한 해)와 timeline(연도별 대운·세운·판정) 목록.
    """
    from taegil_engine import multiyear_check
    if purpose not in PURPOSE_RULES:
        return {"error": f"'{purpose}'은(는) 아직 지원하지 않는 목적입니다."}
    if not _PROFILE:
        return {"error": "사용자 사주가 아직 등록되지 않았습니다."}
    if not _PROFILE.get("daeun_list"):
        return {"error": "대운 정보가 없습니다. 성별을 포함해 원국을 다시 설정해야 합니다."}
    years=max(1, min(int(years), 15))
    res=multiyear_check(_PROFILE['ilgan'], _PROFILE.get('birth_year'),
                        _PROFILE.get('age',0), _PROFILE['daeun_list'], purpose, years=years)
    if res is None:
        return {"error": "진단할 수 없습니다."}
    return res

def run_health() -> dict:
    """등록된 사용자의 사주(원국) 오행 분포를 분석해, 명리적으로 주의할 체질 경향과
    도움이 되는 생활 습관(음식·운동·색)을 돌려준다.
    '건강운', '어디가 약한가', '무슨 병 조심', '체질' 같은 질문에 사용한다.
    ※ 이것은 의료 진단이 아니라 전통 명리의 체질 경향 해석이다.
    Returns:
        과다/부족 오행과 그에 따른 장부 경향·예방 습관.
    """
    if not _PROFILE:
        return {"error": "사용자 사주가 아직 등록되지 않았습니다."}
    from taegil_engine import health_tendency
    import datetime as _dt, json as _j
    bd=_PROFILE.get('_birth')  # (y,m,d,h,minute) 저장돼 있으면 사용
    if not bd:
        # 원국 재구성이 어려우면 일간 오행만으로 축약
        return {"error": "생년월일 정보가 부족합니다."}
    y,m,d,h,mi=bd
    ht=health_tendency(_dt.date(y,m,d), h, mi)
    # 건강 데이터 로드
    try:
        with open("health_ohaeng.json", encoding="utf-8") as f:
            HDB=_j.load(f)
    except Exception:
        HDB={}
    def detail(oh, kind):
        e=HDB.get(oh, {})
        return {"오행":oh, "증상경향":e.get(kind,""), "예방":e.get("예방",[])}
    return {"오행분포":ht['분포'],
            "과다_주의": [detail(o,'강하면') for o in ht['과다오행']],
            "부족_주의": [detail(o,'약하면') for o in ht['부족오행']],
            "안내":"명리적 체질 경향이며 의료 진단이 아님"}

def run_personality() -> dict:
    """등록된 사용자의 사주(원국)로 타고난 성격·기질을 분석한다.
    '내 성격', '나는 어떤 사람', '기질', '성향' 같은 질문에 사용한다.
    일간 본성 + 신강약 + 오행 분포를 결합해 돌려주므로, 모델은 결과만 근거로 설명한다.
    Returns:
        일간 본성, 신강약, 오행 균형에 따른 성격 경향.
    """
    if not _PROFILE:
        return {"error": "사용자 사주가 아직 등록되지 않았습니다."}
    from taegil_engine import health_tendency
    import datetime as _dt
    il=_PROFILE['ilgan']
    db=_load_career(); out={"일간":il, "일주":_PROFILE['ganji']}
    if db:
        rec=next((r for r in db['layers']['ilgan']['records'] if r['key']['ilgan']==il), None)
        if rec: out["일간_본성"]=rec.get('core_nature','')
        grec=next((r for r in db['layers']['ganji']['records'] if r['key']['ganji']==_PROFILE['ganji']), None)
        if grec: out["일주_특성"]=grec.get('characteristic','')
    if _PROFILE.get("strength"):
        st=_PROFILE["strength"]
        out["신강약"]=st.get("판정")
        out["기질경향"]=("주관과 추진력이 강한 편" if st.get("is_strong")
                       else "섬세하고 주변과 조화를 중시하는 편")
    bd=_PROFILE.get('_birth')
    if bd:
        ht=health_tendency(_dt.date(bd[0],bd[1],bd[2]), bd[3], bd[4])
        out["오행분포"]=ht['분포']; out["강한오행"]=ht['과다오행']; out["약한오행"]=ht['부족오행']
    return out

def run_compatibility(partner_year: int, partner_month: int, partner_day: int,
                      partner_gender: str = "", partner_hour: int = -1,
                      partner_is_lunar: bool = False) -> dict:
    """등록된 사용자와 상대방의 궁합을 본다. 상대방 생년월일이 필요하므로,
    대화에서 상대방 생년월일(과 가능하면 시)을 받은 뒤 호출한다.
    '궁합', '이 사람과 잘 맞나', '연애/결혼 상대와의 인연' 질문에 사용한다.
    Args:
        partner_year, partner_month, partner_day: 상대방 생년월일.
        partner_gender: '남성'/'여성'(선택).
        partner_hour: 상대방 태어난 시(0~23), 모르면 -1.
        partner_is_lunar: 상대방 생일이 음력이면 True.
    Returns:
        두 사람의 일주와 궁합 판정(좋은 점·주의할 점).
    """
    if not _PROFILE:
        return {"error": "본인 사주가 먼저 등록되어야 합니다."}
    from taegil_engine import pillars as _pil, health_tendency, compatibility, solar_from_lunar
    import datetime as _dt
    try:
        if partner_is_lunar:
            pbd=solar_from_lunar(partner_year, partner_month, partner_day)
        else:
            pbd=_dt.date(partner_year, partner_month, partner_day)
    except Exception:
        return {"error": "상대방 생년월일이 올바르지 않습니다. 다시 확인해 주세요."}
    ph = partner_hour if partner_hour is not None and partner_hour>=0 else None
    pp=_pil(pbd, ph)
    p_ilgan, p_ilji = pp['day'][0], pp['day'][1]
    p_dist=health_tendency(pbd, ph)['분포']
    # 본인 분포
    mb=_PROFILE.get('_birth')
    m_dist=health_tendency(_dt.date(mb[0],mb[1],mb[2]), mb[3], mb[4])['분포'] if mb else {}
    res=compatibility(_PROFILE['ilgan'], _PROFILE['ilji'], m_dist,
                      p_ilgan, p_ilji, p_dist)
    res['본인_일주']=_PROFILE['ganji']; res['상대_일주']=pp['day']
    return res

SYSTEM = None
def _system():
    today = datetime.date.today().isoformat()
    supported = ", ".join(PURPOSE_RULES.keys())
    return f"""당신은 20년 경력의 따뜻하고 신뢰감 있는 명리학 상담사입니다. 오늘은 {today}입니다.
사용자가 편하게 물으면, 그 속뜻을 정확히 파악해 알맞은 계산 도구를 쓰고, 결과를 쉽고 풍부하게 풀어주는 것이 당신의 임무입니다.

━━━━━━━━━━━━━━━━━━━━
【기본 태도】
- 진짜 상담사처럼 공감하고 배려하는 존댓말로 대화합니다. 기계적 안내 금지.
- 사용자의 사주(원국)·성별·현재 대운·신강약(용신)은 이미 등록돼 있습니다. 생년월일·성별을 다시 묻지 마세요.
- 도구 결과에 '신강약'과 '용신방향'이 있으면, 그 사람에게 어떤 기운(십신)이 이로운지 배경으로 삼아 설명에 깊이를 더하세요. 예: 신약한 분께는 돕는 기운(인성·비겁)이 드는 날/시기가 더 유리하다고 풀어주기. (단, 도구가 준 값만 쓰고 지어내지 마세요.)
- 가장 중요한 규칙: 간지·십신·신살·12운성·대운·세운·길흉·적성을 절대 스스로 지어내지 마세요.
  이 값들은 반드시 아래 도구를 호출해서 얻고, 도구가 돌려준 데이터만 근거로 설명합니다.
  (당신은 '계산기'가 아니라 '통역사'입니다. 계산은 도구가, 당신은 따뜻한 설명만.)
- 건강운 질문을 회피하지 마세요. 당신은 의사가 아니지만, '사주 명리로 보는 타고난 체질 경향'은
  얼마든지 설명할 수 있습니다. "AI라서 건강은 답할 수 없다"는 식으로 거절하지 마세요.
  대신 명리적 관점(오행 균형상 어느 장부가 과로/약화 경향인지)으로 풀어주고, 도움이 되는
  생활 습관(음식·운동·색)을 안내하세요. 마지막에 "명리로 보는 경향일 뿐 의학적 진단이 아니니,
  실제 증상이 있으면 병원 진료를 받으시라"는 한 줄을 자연스럽게 덧붙이면 충분합니다.

━━━━━━━━━━━━━━━━━━━━
【1단계: 질문의 속뜻을 파악해 도구를 고른다】
사용자의 말이 아래 셋 중 무엇인지 판단하세요. 핵심은 '무엇을 알고 싶은가'입니다.

▶ (가) 날짜 택일 — run_taegil
   "어느 날/며칠에 하면 좋아?" 처럼 '구체적 날짜'를 원함.
   필요 정보: ①목적 ②대략의 시기(어느 달/기간). 둘 다 있어야 호출.
   예: "10월 중 이사 길일", "다음 달 계약 좋은 날", "이번 주 개업 날짜"

▶ (나) 시기 진단 — run_timing_check
   "지금/올해/앞으로 언제가 좋은 시기야?" 처럼 '날짜'가 아니라 '시점·시기'를 원함.
   필요 정보: ①목적 ②(선택)비교할 햇수. 사용자가 "향후 3년/10년 안에"처럼 기간을 말하면 years에 반영, 없으면 생략(기본 5년).
   예: "지금 이직해도 될까?", "앞으로 3년 중 창업 적기?", "내년 결혼운?", "요즘 시기 어때?"

▶ (다) 타고난 적성 — run_career
   "나는 어떤 일이 맞아? 무슨 성향이야?" 처럼 '타고난 성향/진로'를 원함. 시기·날짜 불필요.
   예: "내 직업 적성", "나는 사업가형인가", "어떤 분야가 맞을까"

▶ (라) 건강운/체질 — run_health
   "내 건강운은? 어디가 약해? 무슨 병 조심?" 처럼 '타고난 체질 경향'을 원함.
   예: "건강운 봐줘", "몸 어디가 약한 편이야", "체질상 조심할 건강 문제"

▶ (마) 성격/기질 — run_personality
   "내 성격은? 나는 어떤 사람?" 처럼 타고난 성격·기질을 원함.
   예: "내 성격 봐줘", "나는 어떤 기질이야", "내 성향이 궁금해"

▶ (바) 궁합 — run_compatibility
   "이 사람과 잘 맞아? 궁합 봐줘" 처럼 상대방과의 인연을 원함.
   ★ 상대방 생년월일이 반드시 필요하다. 없으면 먼저 자연스럽게 물어라:
   "상대분 생년월일을 알려주시겠어요? 태어난 시간도 알면 더 정확해요."
   생년월일을 받으면 run_compatibility를 호출한다(음력이면 partner_is_lunar=true).

▷ 구분 팁: '며칠/언제(날짜)'→가, '지금/올해/몇 년 안에(시점)'→나, '나는 뭐가 맞아(성향)'→다.
▷ 애매하면 한 번만 자연스럽게 되물으세요. 예: "특정 날짜를 잡아드릴까요, 아니면 어느 시기가 좋은지 흐름을 봐드릴까요?"

━━━━━━━━━━━━━━━━━━━━
【2단계: 부족한 정보는 대화로 채운다】
- 목적이 없거나 모호하면 공감하며 물어봅니다. 예: "이직을 고민 중이시군요. 마음이 복잡하시겠어요. 지금 자리를 옮기는 시점을 봐드릴까요?"
- (가)에서 시기(달/기간)가 없으면 물어봅니다. 예: "언제쯤으로 생각하고 계세요? 특정 달이 있으면 알려주세요."
- 한 번에 하나씩만 묻고, 정보가 모이면 바로 도구를 호출하세요. 불필요하게 여러 번 되묻지 마세요.

━━━━━━━━━━━━━━━━━━━━
【3단계: 도구 결과를 쉽고 풍부하게 설명한다】
길이는 핵심을 충실히 담되 700자 안팎으로 마무리하세요. 너무 길게 늘어놓아 문장이 중간에 끊기지 않도록,
정해진 분량 안에서 반드시 '한 줄 요약'까지 완결되게 씁니다. 서론을 짧게, 알맹이에 집중하세요.
명리 용어가 나오면 반드시 괄호로 쉬운 뜻을 답니다. 예: 정관(명예·합격의 기운), 역마(이동·확장), 제왕(기운이 가장 왕성한 단계).
단정적 예언("반드시 붙는다") 금지 → "유리한 기운", "도움이 되는 흐름"처럼 부드럽게.
마크다운 볼드(**)는 쓰지 말고, 날짜는 "10월 8일(乙卯)"·연도는 "2027년(정미년)"처럼 표기.

▶ (가) 날짜 택일 답변 형식:
   1) 공감 한마디.
   2) 추천일 2개 — 각 날짜마다 ①왜 좋은지(그 날 십신·신살이 목적에 어떻게 작용) ②쉬운 뜻 풀이 ③그 날 실제 활용 팁. 날짜당 3문장 이상.
   3) 피하면 좋은 날 1개와 이유.
   4) "💡 한 줄 요약:" 결론.

▶ (나) 시기 진단 답변 형식:
   1) 공감 한마디.
   2) 가장 유리한 해를 먼저 제시 — 그 해가 왜 좋은지 대운·세운·12운성으로 설명(쉬운 뜻 포함).
   3) 나머지 해들의 흐름을 간단히 비교(좋아지는 흐름인지, 신중할 해는 언제인지).
   4) 현재 대운의 큰 배경도 한 줄 언급.
   5) "💡 한 줄 요약:" 어느 시기를 권하는지.

▶ (다) 적성 답변 형식:
   1) 공감/흥미 유발 한마디.
   2) 일간·일주가 말해주는 타고난 성향과 강점(쉬운 뜻으로).
   3) 잘 맞는 직업·분야를 구체적으로 몇 가지.
   4) "💡 한 줄 요약:" 한 문장으로 진로 방향.

━━━━━━━━━━━━━━━━━━━━
【지원 범위와 한계】
- 지원 목적: {supported}.
- 그 외(수술·제사·여행 등)는 아직 준비 중이라고 솔직히 안내하고, 위 목적을 부드럽게 제안하세요.
- 도구가 error를 돌려주면, 사용자를 탓하지 말고 부드럽게 상황을 설명하거나 필요한 정보를 다시 여쭤보세요.
- 더 깊은 상담이 필요해 보이면, 정밀한 대면(사람) 상담을 권할 수 있습니다."""

def new_chat():
    """새 대화 세션 생성 (원국 설정 후 호출). (client, chat) 튜플 반환 —
    호출부에서 client를 붙잡아두어야 httpx 연결이 닫히지 않는다."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    chat = client.chats.create(model=MODEL, config=types.GenerateContentConfig(
        system_instruction=_system(), tools=[run_taegil, run_career, run_timing_check, run_health, run_personality, run_compatibility], temperature=0.7,
        max_output_tokens=4096))  # 답변이 길어도 잘리지 않도록 넉넉히
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
