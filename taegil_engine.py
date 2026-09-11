# -*- coding: utf-8 -*-
"""택일(擇日) 엔진 v1 — lunar_python 기반 (순수 파이썬, 절기 정확)
필요: pip install lunar_python"""
import datetime
from lunar_python import Solar

GAN_OH={'甲':'木','乙':'木','丙':'火','丁':'火','戊':'土','己':'土','庚':'金','辛':'金','壬':'水','癸':'水'}
GAN_YY={'甲':1,'丙':1,'戊':1,'庚':1,'壬':1,'乙':0,'丁':0,'己':0,'辛':0,'癸':0}
ZHI_JEONGGI={'子':'癸','丑':'己','寅':'甲','卯':'乙','辰':'戊','巳':'丙','午':'丁','未':'己','申':'庚','酉':'辛','戌':'戊','亥':'壬'}
SAENG={'木':'火','火':'土','土':'金','金':'水','水':'木'}
GEUK={'木':'土','土':'水','水':'火','火':'金','金':'木'}
ZHI=['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']
SAMHAP_GROUP={'申':'水','子':'水','辰':'水','寅':'火','午':'火','戌':'火','巳':'金','酉':'金','丑':'金','亥':'木','卯':'木','未':'木'}
SINSAL_ORDER=['겁살','재살','천살','지살','년살','월살','망신','장성','반안','역마','육해','화개']
SINSAL_START={'水':'巳','火':'亥','金':'寅','木':'申'}

def sipsin(ilgan, target_gan):
    io,iy=GAN_OH[ilgan],GAN_YY[ilgan]; to,ty=GAN_OH[target_gan],GAN_YY[target_gan]; same=(iy==ty)
    if io==to: return '비견' if same else '겁재'
    if SAENG[io]==to: return '식신' if same else '상관'
    if GEUK[io]==to: return '편재' if same else '정재'
    if GEUK[to]==io: return '편관' if same else '정관'
    if SAENG[to]==io: return '편인' if same else '정인'
    return '?'
def sipsin_of_jiji(ilgan, jiji): return sipsin(ilgan, ZHI_JEONGGI[jiji])
def sinsal_of(wonguk_jiji, target_jiji):
    kuk=SAMHAP_GROUP[wonguk_jiji]; si=ZHI.index(SINSAL_START[kuk])
    return {ZHI[(si+i)%12]:SINSAL_ORDER[i] for i in range(12)}[target_jiji]

def _apply_true_solar(dt, hour, minute, longitude=127.0):
    """진태양시 보정: 한국(동경127°)은 표준시(135°) 대비 약 -32분.
    보정 후 날짜가 바뀔 수 있으므로 datetime으로 계산해 되돌려준다."""
    import datetime as _dt
    base=_dt.datetime(dt.year,dt.month,dt.day,hour,minute)
    offset_min=(longitude-135.0)*4      # 경도 1도 = 4분, 127°면 약 -32분
    corrected=base+_dt.timedelta(minutes=offset_min)
    return corrected

def _lunar(dt, hour=None, minute=0, true_solar=True):
    if hour is None:
        return Solar.fromYmd(dt.year,dt.month,dt.day).getLunar()
    if true_solar:
        c=_apply_true_solar(dt,hour,minute)
        return Solar.fromYmdHms(c.year,c.month,c.day,c.hour,c.minute,0).getLunar()
    return Solar.fromYmdHms(dt.year,dt.month,dt.day,hour,minute,0).getLunar()

def pillars(dt, hour=None, minute=0, true_solar=True, gender=None, target_age=None):
    """절기 정확한 년/월/일(+시) 간지. hour/minute 주면 시주까지, 진태양시 보정 적용.
    gender(1=남,0=여) 주면 대운(大運)도 계산해 포함 (성별에 따라 순행/역행)."""
    lu=_lunar(dt,hour,minute,true_solar); ec=lu.getEightChar()
    out={'year':ec.getYear(),'month':ec.getMonth(),'day':ec.getDay(),
         'tianshen_luck':lu.getDayTianShenLuck(),
         'zhixing':lu.getZhiXing()}
    if hour is not None:
        out['hour']=ec.getTime()   # 시주(時柱)
    out['strength']=analyze_strength(ec)   # 신강/신약 + 용신방향
    if gender is not None:
        yun=ec.getYun(1 if gender==1 else 0)
        das=yun.getDaYun()
        out['daeun_forward']=yun.isForward()
        out['daeun_start_age']=das[1].getStartAge() if len(das)>1 else None
        out['daeun_list']=[{'start':d.getStartAge(),'end':d.getEndAge(),'ganzhi':d.getGanZhi()}
                           for d in das[1:11]]
        # 현재(또는 지정 나이) 대운 찾기
        age = target_age if target_age is not None else _age_now(dt)
        cur=None
        for d in das[1:]:
            if d.getStartAge() <= age <= d.getEndAge():
                cur={'start':d.getStartAge(),'end':d.getEndAge(),'ganzhi':d.getGanZhi()}; break
        out['daeun_current']=cur
        out['age']=age
    return out

def _age_now(birth_date):
    import datetime as _dt
    t=_dt.date.today()
    return t.year - birth_date.year - ((t.month,t.day)<(birth_date.month,birth_date.day))

def solar_from_lunar(year, month, day, leap=False):
    """음력 → 양력 date 변환. leap=True면 윤달."""
    from lunar_python import Lunar
    import datetime as _dt
    m = -month if leap else month
    s = Lunar.fromYmd(year, m, day).getSolar()
    return _dt.date(s.getYear(), s.getMonth(), s.getDay())

# ---------- 신강/신약 판정 (억부) ----------
_JIJI_HIDDEN={'子':[('癸',1.0)],'丑':[('己',0.6),('癸',0.2),('辛',0.2)],
 '寅':[('甲',0.6),('丙',0.3),('戊',0.1)],'卯':[('乙',1.0)],
 '辰':[('戊',0.6),('乙',0.2),('癸',0.2)],'巳':[('丙',0.6),('庚',0.2),('戊',0.2)],
 '午':[('丁',0.7),('己',0.3)],'未':[('己',0.6),('丁',0.2),('乙',0.2)],
 '申':[('庚',0.6),('壬',0.2),('戊',0.2)],'酉':[('辛',1.0)],
 '戌':[('戊',0.6),('辛',0.2),('丁',0.2)],'亥':[('壬',0.7),('甲',0.3)]}
_MONTH_WANG={'寅':'木','卯':'木','巳':'火','午':'火','申':'金','酉':'金','亥':'水','子':'水',
             '辰':'土','戌':'土','丑':'土','未':'土'}

def _supports(day_oh, other_oh):
    """other 오행이 일간을 돕는가: 같은 오행(비겁) 또는 나를 생함(인성)."""
    if other_oh==day_oh: return True
    if SAENG[other_oh]==day_oh: return True
    return False

def analyze_strength(ec):
    """팔자로 신강/신약을 억부식으로 판정(득령+득세)."""
    day_gan=ec.getDay()[0]; day_oh=GAN_OH[day_gan]
    pillars_gz=[ec.getYear(),ec.getMonth(),ec.getDay(),ec.getTime()]
    month_ji=ec.getMonth()[1]
    deukryeong=_supports(day_oh, _MONTH_WANG[month_ji])
    support=0.0; total=0.0
    for gz in pillars_gz:            # 천간(일간 제외)
        g=gz[0]
        if g!=day_gan:
            total+=1.0
            if _supports(day_oh, GAN_OH[g]): support+=1.0
    for gz in pillars_gz:            # 지장간
        for hg,w in _JIJI_HIDDEN[gz[1]]:
            total+=w
            if _supports(day_oh, GAN_OH[hg]): support+=w
    ratio = support/total if total else 0
    adj = ratio + (0.12 if deukryeong else -0.12)
    if adj>=0.62: level='매우 신강'
    elif adj>=0.50: level='신강'
    elif adj>=0.40: level='중화(신강 쪽)'
    elif adj>=0.30: level='중화(신약 쪽)'
    elif adj>=0.20: level='신약'
    else: level='매우 신약'
    is_strong = adj>=0.45
    if is_strong:
        yongsin=['식상','재성','관성']; help_type='기운을 덜어내고 조절하는'
    else:
        yongsin=['인성','비겁']; help_type='기운을 북돋우고 돕는'
    return {'일간':day_gan,'일간오행':day_oh,'득령':deukryeong,
            '세력비':round(ratio,2),'판정':level,'is_strong':is_strong,
            '용신방향':yongsin,'용신설명':help_type}

def strength_for(dt, hour=None, minute=0, true_solar=True):
    ec=_lunar(dt,hour,minute,true_solar).getEightChar()
    return analyze_strength(ec)

# ---------- 오행 분포 & 건강 경향 ----------
def ohaeng_distribution(ec):
    """팔자의 오행 세력 분포(천간+지장간 가중)를 집계."""
    dist={'木':0.0,'火':0.0,'土':0.0,'金':0.0,'水':0.0}
    for gz in [ec.getYear(),ec.getMonth(),ec.getDay(),ec.getTime()]:
        dist[GAN_OH[gz[0]]]+=1.0
        for hg,w in _JIJI_HIDDEN[gz[1]]:
            dist[GAN_OH[hg]]+=w
    total=sum(dist.values()) or 1
    return {k:round(v/total,3) for k,v in dist.items()}

def health_tendency(dt, hour=None, minute=0, true_solar=True):
    """오행 분포로 과다(强)·부족(弱) 오행을 찾아 건강 경향 데이터의 키를 돌려준다.
    실제 증상/예방 텍스트는 health_ohaeng.json에서 조회(에이전트가 결합)."""
    ec=_lunar(dt,hour,minute,true_solar).getEightChar()
    dist=ohaeng_distribution(ec)
    avg=1/5
    strong=[k for k,v in dist.items() if v>=avg*1.8]   # 뚜렷이 과다
    weak=[k for k,v in dist.items() if v<=avg*0.4]      # 뚜렷이 부족
    # 하나도 안 잡히면 최다/최소 하나씩
    order=sorted(dist.items(), key=lambda x:-x[1])
    if not strong: strong=[order[0][0]]
    if not weak: weak=[order[-1][0]]
    return {'분포':dist,'과다오행':strong,'부족오행':weak}

def lunar_day(dt): return _lunar(dt).getDay()  # 음력 날짜(손없는날 판정용)

# ---------- 궁합(합충) ----------
CHEONGAN_HAP={('甲','己'),('乙','庚'),('丙','辛'),('丁','壬'),('戊','癸')}
JIJI_YUKHAP={('子','丑'),('寅','亥'),('卯','戌'),('辰','酉'),('巳','申'),('午','未')}
JIJI_CHUNG={('子','午'),('丑','未'),('寅','申'),('卯','酉'),('辰','戌'),('巳','亥')}
def _pair_in(a,b,pairs): return (a,b) in pairs or (b,a) in pairs

def compatibility(ilgan1, ilji1, dist1, ilgan2, ilji2, dist2):
    """두 사람의 일간·일지·오행분포로 궁합을 점수화."""
    score=0; plus=[]; minus=[]
    # 1) 일간 천간합 (강한 이끌림)
    if _pair_in(ilgan1, ilgan2, CHEONGAN_HAP):
        score+=3; plus.append('일간 천간합(서로 끌리는 기운)')
    # 2) 일지 관계
    if _pair_in(ilji1, ilji2, JIJI_YUKHAP):
        score+=3; plus.append('일지 육합(부부 화합의 기운)')
    elif ilji1 in SAMHAP_GROUP and SAMHAP_GROUP[ilji1]==SAMHAP_GROUP.get(ilji2) and ilji1!=ilji2:
        score+=2; plus.append('일지 삼합(뜻이 통하는 기운)')
    if _pair_in(ilji1, ilji2, JIJI_CHUNG):
        score-=3; minus.append('일지 충(부딪히기 쉬운 기운)')
    # 3) 일간 오행 상생/상극
    o1,o2=GAN_OH[ilgan1],GAN_OH[ilgan2]
    if o1==o2: plus.append('같은 오행(비슷한 기질)')
    elif SAENG[o1]==o2 or SAENG[o2]==o1: score+=2; plus.append('오행 상생(서로 북돋움)')
    elif GEUK[o1]==o2 or GEUK[o2]==o1: score-=1; minus.append('오행 상극(주도권 갈등 주의)')
    # 4) 오행 보완: 한쪽 부족을 다른쪽이 채워주는가
    for oh in ['木','火','土','金','水']:
        if dist1.get(oh,0)<0.08 and dist2.get(oh,0)>=0.25:
            score+=1; plus.append(f'{oh} 보완(상대가 채워줌)'); break
    verdict=('매우 좋음' if score>=6 else '좋음' if score>=3 else
             '무난' if score>=0 else '노력 필요' if score>=-3 else '주의')
    return {'점수':score,'판정':verdict,'좋은점':plus,'주의점':minus}

# ---------- 12운성(십이운성) & 대운 시기 진단 ----------
CHANGSAENG_START={'甲':'亥','丙':'寅','戊':'寅','庚':'巳','壬':'申',
                  '乙':'午','丁':'酉','己':'酉','辛':'子','癸':'卯'}
_YANG=set('甲丙戊庚壬')
_STAGES=['長生','沐浴','冠帶','建祿','帝旺','衰','病','死','墓','絶','胎','養']
_STAGE_KR={'長生':'장생','沐浴':'목욕','冠帶':'관대','建祿':'건록','帝旺':'제왕','衰':'쇠',
           '病':'병','死':'사','墓':'묘','絶':'절','胎':'태','養':'양'}
_STAGE_STRENGTH={'長生':3,'沐浴':1,'冠帶':2,'建祿':4,'帝旺':5,'衰':1,'病':-1,'死':-3,
                 '墓':-2,'絶':-3,'胎':0,'養':2}

def unseong(ilgan, jiji):
    """일간이 특정 지지에서 갖는 12운성 단계(양간 순행/음간 역행)."""
    si=ZHI.index(CHANGSAENG_START[ilgan]); step=1 if ilgan in _YANG else -1
    for k in range(12):
        if ZHI[(si+step*k)%12]==jiji: return _STAGES[k]
    return None

def daeun_check(ilgan, wonguk_jiji, daeun_ganzhi, purpose):
    """현재 대운이 특정 목적에 유리한 시기인지 진단.
    (1) 대운 천간·지지의 십신이 목적의 길/흉 십신에 맞는지
    (2) 대운 지지의 12운성 강약(일간 기준)
    두 축을 합쳐 점수화."""
    if purpose not in PURPOSE_RULES: return None
    r=PURPOSE_RULES[purpose]
    d_gan, d_ji = daeun_ganzhi[0], daeun_ganzhi[1]
    ss_gan=sipsin(ilgan, d_gan); ss_ji=sipsin_of_jiji(ilgan, d_ji)
    score=0; reasons=[]
    for ss in (ss_gan, ss_ji):
        if ss in r['good_sipsin']: score+=r['good_sipsin'][ss]; reasons.append(f'+{ss}')
        elif ss in r['bad_sipsin']: score+=r['bad_sipsin'][ss]; reasons.append(f'-{ss}')
    stage=unseong(ilgan, d_ji)
    st=_STAGE_STRENGTH.get(stage,0)
    score+=st
    reasons.append(f'{_STAGE_KR.get(stage,stage)}({st:+d})')
    verdict=('매우 유리' if score>=5 else '유리' if score>=2 else
             '보통' if score>=-1 else '신중' if score>=-4 else '불리')
    return {'daeun':daeun_ganzhi,'십신':f'{ss_gan}/{ss_ji}',
            '12운성':_STAGE_KR.get(stage,stage),'강약점수':st,
            'total':score,'verdict':verdict,'reasons':reasons}

def _score_ganzhi(ilgan, ganzhi, purpose):
    """간지 하나(대운 또는 세운)를 목적에 대해 점수화. (십신 + 12운성)"""
    r=PURPOSE_RULES[purpose]
    g, j = ganzhi[0], ganzhi[1]
    ss_gan=sipsin(ilgan, g); ss_ji=sipsin_of_jiji(ilgan, j)
    sc=0; rs=[]
    for ss in (ss_gan, ss_ji):
        if ss in r['good_sipsin']: sc+=r['good_sipsin'][ss]; rs.append(f'+{ss}')
        elif ss in r['bad_sipsin']: sc+=r['bad_sipsin'][ss]; rs.append(f'-{ss}')
    stage=unseong(ilgan, j); st=_STAGE_STRENGTH.get(stage,0); sc+=st
    return sc, ss_gan, ss_ji, _STAGE_KR.get(stage,stage), st, rs

def _verdict(score):
    return ('매우 유리' if score>=6 else '유리' if score>=2.5 else
            '보통' if score>=-1.5 else '신중' if score>=-5 else '불리')

def _daeun_at_age(daeun_list, age):
    """특정 나이에 해당하는 대운 간지를 찾음(없으면 가장 가까운 것)."""
    for d in daeun_list:
        if d['start'] <= age <= d['end']: return d
    return daeun_list[-1] if daeun_list else None

def multiyear_check(ilgan, birth_year, cur_age, daeun_list, purpose,
                    years=5, se_weight=1.2, dae_weight=1.0):
    """향후 여러 해를 '대운(그 해 나이의 대운) + 세운(그 해 간지)'로 종합 점수화해 비교.
    대운이 중간에 바뀌면 그 해 나이에 맞는 대운을 다시 찾아 반영."""
    if purpose not in PURPOSE_RULES: return None
    import datetime as _dt
    this_year=_dt.date.today().year
    rows=[]
    for k in range(years):
        yr=this_year+k
        age=cur_age+k
        # 그 해 세운 간지
        se=pillars(_dt.date(yr,6,1))['year']   # 6월 기준이면 그 해 세운 확정
        dae=_daeun_at_age(daeun_list, age)
        se_sc, se_g, se_j, se_stage, se_st, se_rs = _score_ganzhi(ilgan, se, purpose)
        dae_sc=0; dae_gz=None; dae_stage=None
        if dae:
            dae_sc, dg, dj, dae_stage, dae_st, dae_rs = _score_ganzhi(ilgan, dae['ganzhi'], purpose)
            dae_gz=dae['ganzhi']
        total = dae_weight*dae_sc + se_weight*se_sc
        rows.append({'year':yr,'age':age,'sewoon':se,'sewoon_십신':f'{se_g}/{se_j}',
                     'sewoon_12운성':se_stage,'daeun':dae_gz,'daeun_12운성':dae_stage,
                     'total':round(total,1),'verdict':_verdict(total)})
    ranked=sorted(rows, key=lambda x:-x['total'])
    return {'purpose':purpose,'years':years,'best':ranked[0],'timeline':rows,'ranked':ranked}

PURPOSE_RULES={
 '합격/시험/지원':{'good_sipsin':{'정인':3,'편인':2,'정관':3,'식신':1},
                'bad_sipsin':{'상관':-3,'겁재':-2,'편관':-1},
                'good_sinsal':{'장성':2,'반안':2,'역마':1,'화개':1},
                'bad_sinsal':{'겁살':-2,'재살':-2,'육해':-1},
                'desc':'문서·시험은 인성(印)과 정관을 반기고, 관을 극하는 상관·경쟁하는 겁재를 꺼림'},
 '이사/이동':{'good_sipsin':{'정재':1,'편재':1,'식신':1},'bad_sipsin':{'겁재':-2,'상관':-1},
            'good_sinsal':{'역마':3,'지살':2,'반안':1},'bad_sinsal':{'겁살':-2,'재살':-2,'월살':-1},
            'desc':'이동은 역마·지살을 반기고, 손재하는 겁살·재살을 꺼림'},
 '이직/취업':{'good_sipsin':{'정관':3,'편관':2,'정인':2,'정재':1},
            'bad_sipsin':{'상관':-3,'겁재':-2},
            'good_sinsal':{'역마':3,'반안':2,'장성':2,'지살':1},
            'bad_sinsal':{'겁살':-2,'재살':-2,'월살':-1},
            'desc':'이직·취업은 직장의 관성과 자리 옮김의 역마를 반기고, 관을 극하는 상관·경쟁하는 겁재를 꺼림'},
 '개업/창업':{'good_sipsin':{'정재':3,'편재':3,'식신':2,'정관':1},
            'bad_sipsin':{'겁재':-3,'편인':-2,'상관':-1},
            'good_sinsal':{'지살':2,'역마':2,'장성':2,'반안':1},
            'bad_sinsal':{'겁살':-3,'재살':-2,'월살':-2},
            'desc':'개업·창업은 재물의 재성과 생산·영업의 식신을 반기고, 재물을 겁탈하는 겁재·돌발의 겁살을 크게 꺼림'},
 '계약/거래':{'good_sipsin':{'정재':3,'정관':2,'정인':2,'식신':1},
            'bad_sipsin':{'상관':-3,'겁재':-2,'편관':-1},
            'good_sinsal':{'반안':2,'장성':1},
            'bad_sinsal':{'겁살':-2,'재살':-2,'육해':-1,'년살':-1},
            'desc':'계약은 신용의 정재와 약속·질서의 정관, 문서의 인성을 반기고, 구설의 상관·손재의 겁재를 꺼림'},
 '혼인/결혼':{'good_sipsin':{'정관':2,'정재':2,'정인':1,'식신':1},
            'bad_sipsin':{'상관':-2,'겁재':-2,'편관':-1},
            'good_sinsal':{'반안':2,'화개':1,'장성':1},
            'bad_sinsal':{'겁살':-2,'재살':-2,'월살':-2,'년살':-2},
            'desc':'혼인은 안정의 정관·정재와 화합의 기운을 반기고, 구설·도화(년살)·손재를 꺼림 (전통 혼인택일은 더 복잡하니 참고용)'},
}

def _sipsin_group(ss):
    """십신을 5그룹으로: 비겁/식상/재성/관성/인성."""
    return {'비견':'비겁','겁재':'비겁','식신':'식상','상관':'식상',
            '편재':'재성','정재':'재성','편관':'관성','정관':'관성',
            '편인':'인성','정인':'인성'}.get(ss)

def score_day(dt, wonguk_ilgan, wonguk_jiji, purpose, yongsin=None):
    p=pillars(dt); r=PURPOSE_RULES[purpose]
    day_gan,day_ji=p['day'][0],p['day'][1]
    ss_gan=sipsin(wonguk_ilgan,day_gan); ss_ji=sipsin_of_jiji(wonguk_ilgan,day_ji)
    sinsal=sinsal_of(wonguk_jiji,day_ji)
    score=0; reasons=[]
    for ss in (ss_gan,ss_ji):
        if ss in r['good_sipsin']: score+=r['good_sipsin'][ss]; reasons.append(f'+{ss}')
        if ss in r['bad_sipsin']: score+=r['bad_sipsin'][ss]; reasons.append(f'-{ss}')
    if sinsal in r['good_sinsal']: score+=r['good_sinsal'][sinsal]; reasons.append(f'+{sinsal}')
    if sinsal in r['bad_sinsal']: score+=r['bad_sinsal'][sinsal]; reasons.append(f'-{sinsal}')
    # 황흑도 가산 (전통 택일)
    if p['tianshen_luck']=='吉': score+=1; reasons.append('+황도')
    elif p['tianshen_luck']=='凶': score-=1; reasons.append('-흑도')
    # 신강약 용신 보정: 그 날 십신이 용신 그룹이면 가점, 기신(반대)이면 감점
    if yongsin:
        for ss in (ss_gan, ss_ji):
            grp=_sipsin_group(ss)
            if grp in yongsin: score+=1.5; reasons.append(f'+용신({grp})')
    ld=lunar_day(dt); son_free= ld%10 in (9,0)
    if son_free: reasons.append('손없는날')
    return {'date':dt.strftime('%Y-%m-%d (%a)'),'day_pillar':p['day'],'십신':f'{ss_gan}/{ss_ji}',
            '신살':sinsal,'건제':p['zhixing'],'황흑도':p['tianshen_luck'],'손없는날':son_free,
            'score':round(score,1),'reasons':reasons}

if __name__=="__main__":
    son=pillars(datetime.date(2007,3,15))
    il,ji=son['day'][0],son['day'][1]
    print(f"아들 원국 일주={son['day']} 세운={son['year']} → 일간 {il}, 일지 {ji}")
    start=datetime.date(2026,10,1)
    res=[score_day(start+datetime.timedelta(days=i),il,ji,'합격/시험/지원') for i in range(31)]
    res.sort(key=lambda x:-x['score'])
    print("\n── 상위 5 길일 (v1: 십신+신살+황흑도) ──")
    for r in res[:5]:
        print(f"{r['date']} {r['day_pillar']} 십신{r['십신']:<9} 신살{r['신살']:<3} 건제{r['건제']} 황흑도{r['황흑도']} {r['score']:+d} {' '.join(r['reasons'])}")
