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

def pillars(dt, hour=None, minute=0, true_solar=True):
    """절기 정확한 년/월/일(+시) 간지. hour/minute 주면 시주까지, 진태양시 보정 적용."""
    lu=_lunar(dt,hour,minute,true_solar); ec=lu.getEightChar()
    out={'year':ec.getYear(),'month':ec.getMonth(),'day':ec.getDay(),
         'tianshen_luck':lu.getDayTianShenLuck(),
         'zhixing':lu.getZhiXing()}
    if hour is not None:
        out['hour']=ec.getTime()   # 시주(時柱)
    return out

def lunar_day(dt): return _lunar(dt).getDay()  # 음력 날짜(손없는날 판정용)

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

def score_day(dt, wonguk_ilgan, wonguk_jiji, purpose):
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
    ld=lunar_day(dt); son_free= ld%10 in (9,0)
    if son_free: reasons.append('손없는날')
    return {'date':dt.strftime('%Y-%m-%d (%a)'),'day_pillar':p['day'],'십신':f'{ss_gan}/{ss_ji}',
            '신살':sinsal,'건제':p['zhixing'],'황흑도':p['tianshen_luck'],'손없는날':son_free,
            'score':score,'reasons':reasons}

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