# -*- coding:utf-8 -*-
import re
import pymssql
from itertools import chain

def get_cslist():
    """获取车型名称列表"""
    conn=pymssql.connect(host='192.168.1.250',database='down',user='sa',password='liangshu@',charset="UTF-8")
    cur=conn.cursor()
    sql="""
    select brandname,carsseriesname,keyword
    from keyword_carsseries
    where srcsys = 'AH'
    """
    cur.execute(sql)
    rows=cur.fetchall()
    rows.sort(key=lambda x:len(x[1]),reverse=True)
    return rows
    
cslist = get_cslist()
    
def match_cs(cslist, strings, count):
    """匹配车型"""
    rmList = {'元','商','QQ','五星','4008','4S','5008','无限','560'}
    res = []
    for cs in cslist:
        if len(res) >= count:
            break
        if cs[1].replace(' ','').lower() in strings.lower():
            if cs[1] in rmList and cs[0].lower() not in strings.lower():
                continue
            else:
                res.append(cs[1])
    cslist.sort(key=lambda x:len(x[2]),reverse=True)
    for cs in cslist:
        if len(res) >= count:
            break
        if cs[2].replace(' ','').lower() in strings.lower():
            if cs[2] in rmList and cs[0].lower() not in strings.lower():
                continue
            else:
                res.append(cs[2])
    if len(res) > 1:
        res.sort(key=lambda x:strings.lower().index(x.replace(' ','').lower()))
    return res

def deal_num(strings):
    """
        处理非统一的数量(字符串)类型，转成统一的阿拉伯数字(字符串)
        例如：['三','一千零五十万','2.5万','五千零二十','4万8千','4千3','二十三万','2.55','5.624万','100万','50w','5k','八千零一']
        结果：['3', '10500000', '25000', '5020', '48000', '4300', '230000', '2.55', '56240', '1000000', '500000', '5000', '8001']
    """
    numDict = {'一':1,'二':2,'两':2,'俩':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'百':100,'千':1000,'k':1000,'K':1000,'万':10000,'w':10000,'W':10000,'亿':10**8}
    try:
        result = int(strings)
    except:
        try:
            result = float(strings)
        except:
            try:
                result = 0
                num = ''
                mul = 1
                for i,x in enumerate(strings):
                    if x in '0123456789.':
                        num += x
                    elif x in '零':
                        mul = 1
                        continue
                    elif x in '十百千万亿kKwW':
                        mulTmp = numDict[x]
                        if i == 0:
                            result = 1
                        if num:
                            if mul == 1 or mulTmp < mul:
                                result += mulTmp * float(num)
                            else:
                                result += num
                                result *= mulTmp
                        else:
                            result *= mulTmp
                        num = ''
                        mul = mulTmp
                    else:
                        try:
                            num = numDict[x]
                        except KeyError as e:
                            print('非法的数量字符串：',e)
                            return strings
                num = num if num else '0'
                mul = (mul // 10) if (mul // 10) else 1
                result = int(result) + int(num) * mul
            except:
                return strings
    return str(result)
    
def deal_dw(strings, dateconver=False):
    """
        处理数据统一单位
        dateconver -- 日期转成xx期
    """
    numDict = {'月':1,'年':12}
    p = [       
        '([一二两俩三四五六七八九十百\d\.]+)?([千万])(?!公里|km|KM)([零一二两俩三四五六七八九十\d]+)?',
        '([一二两俩三四五六七八九十\d]+)个?([年月])',
        '([一二两俩三四五六七八九十百千\d\.]+)((?:次|万公里|万KM|万km))',
    ]
    reg = [re.compile(x) for x in p]
    flagPtn = re.compile('[一二两俩三四五六七八九十年月千万次]')
    result = strings
    if flagPtn.search(strings):
        for i,r in enumerate(reg):
            matchStr = r.findall(strings)
            for ms in matchStr:
                if ms[1] in '千万':
                    tmp = deal_num(''.join(ms))
                elif ms[1] in '年月':
                    if dateconver:
                        if '半' in strings:
                            result = strings.replace('半','')
                            num = float(deal_num(ms[0])+'.5') 
                        else:
                            num = int(deal_num(ms[0])) 
                        tmp = str(int(num * numDict[ms[1]])) + '期'
                    else:
                        tmp = deal_num(ms[0]) + ms[1]
                else:
                    tmp = deal_num(ms[0]) + ms[1]
                result = reg[i].sub(tmp,result)
    return result

def deal_zk(strings):
    """处理数据折扣统一类型"""
    numDict = {'一':'1','二':'2','两':'2','俩':'2','三':'3','四':'4',
        '五':'5','六':'6','七':'7','八':'8','九':'9'}
    pList = [
        '^([全减送]?免(?:100%|费)?|[赠送]{1,2}|免?全额|100%)$',
        '^(送?减半|[省减免]{1,2}50%|五折|半价)$',
        '^(\d{2}|[一二两俩三四五六七八九]{1,2})折$'
    ]
    matchPtn = [re.compile(p) for p in pList]
    for i,mp in enumerate(matchPtn):
        ms = ''.join(mp.findall(strings))
        if ms:
            if i == 0:
                return '0元'
            elif i == 1:
                return '5折'
            else:
                return '.'.join([numDict.get(x,x) for x in ms]) + '折'
    return strings
             
def deal_brand(s):
    """抽置换中，处理品牌类别统一"""
    ptnQ = re.compile('非[本同]|其?[他它余]|外')
    ptnB = re.compile('[本同]')
    ptnR = re.compile('(?:全|任[何意]|不限)')
    if ptnQ.search(s):
        return '其它品牌'
    elif ptnB.search(s):
        return '本品牌'
    elif ptnR.search(s):
        return '任意品牌'
    return s
             
def mianxi(strings):
    '''0息、零息、免息、无息、贴息'''
    pList = [
        '''
        (?<!让利)(?<!优惠)(?<!现金优惠)(?<!现金直降)(?<!礼包)(?<!金融产品与)
        (
            (?:[1-3]?\d|\d{1,2}(?:\.\d{1,2})|[一二两俩三四五六七八九十]{1,3})年半?(?:\d{1,2}(?:\.\d{1,2})?%)?
            |(?:[1-3]?\d|[一二两俩三四五六七八九十]{1,2})(?:[月期](?!供)|个月)(?:\d{1,2}(?:\.\d{1,2})?%)?
            |\d{1,2}(?:\.\d{1,2})?%
            |(?<!\d)[1-9]\d{3,}元?(?!年)(?!款)
            |(?<![\d\.])\d{1,2}(?:\.\d{1,2})?[千万]元?
            |[一二两俩三四五六七八九十][千万][一二两俩三四五六七八九十\d]?元?
        )?
        (?:分期|[】\)）利率超长最高尊享按揭千万\d厂家金融贷款/台辆]{,7})
        ([0零免无]利?[息率]|(?:全额)?贴息)
        (?:[（期限可长达高利息免至贴最更是享受低到]{,5}
            (
                (?:[1-3]?\d|\d{1,2}(?:\.\d{1,2})|[一二两俩三四五六七八九十]{1,3})年半?(?:\d{1,2}(?:\.\d{1,2})?%)?
                |\d{1,2}(?:\.\d{1,2})?%
                |(?:[1-3]?\d|[一二两俩三四五六七八九十]{1,2})(?:[月期](?!供)|个月)(?:\d{1,2}(?:\.\d{1,2})?%)?
                |\d{1,2}(?:\.\d{1,2})?%
                |\d{4,}元?(?!年)(?!款)(?!\d)
                |\d{1,2}(?:\.\d{1,2})?[千万]
                |[一二两俩三四五六七八九十][千万][一二两俩三四五六七八九十\d]?元?
            )?
            (?!低息|元起|起|[定限]额贷|产品)
        )?
        ''',
    ]
    matchPtn = [re.compile(p, re.X) for p in pList]
    flagPtn = re.compile('\d{3,}元?|\d{1,2}(?:\.\d{1,2})?%')
    numPtn = re.compile('(\d{3,})元?(?:\d{3,}元?)?')
    qishuPtn = re.compile('(\d{2}期)\d{2}期')
    
    matchCs = []
    matchStrTmp = [mp.findall(strings) for mp in matchPtn]
    matchStr = []
    for mst in matchStrTmp:
        for ms in mst:
            sjtmp = deal_dw(ms[0]+ms[2],dateconver=True)
            if sjtmp and (ms[1] != '贴息' or flagPtn.search(sjtmp)):
                sjtmp = numPtn.sub('\\1元',sjtmp)
                sj = qishuPtn.sub('\\1',sjtmp)
                lb, nr = '免息', ''
                matchStr.append([lb,sj,nr])
    matchStrCnt = len(matchStr)
    matchCs = match_cs(cslist, strings, matchStrCnt)
    for i,ms in enumerate(matchStr):
        try:
            cs = matchCs[i]
        except IndexError:
            cs = ''
        ms.append(cs)
    
    return matchStr
                
def dikou(strings):
    '''抵扣券、购车券'''
    matchPtn = re.compile('(\d+[千元]{1,2})?(?:意向金|诚意金)?(?:现场[购定订]车|即?可)?[抵扣赠送]{1,2}(\d+[千万元]{1,2})(?:购车基金|购车款|(?:代金|现金|抵值|(?:购车现金)?抵扣|(?:购车)?抵用|购车)券)?')
    
    matchCs = []
    matchStr = []
    matchStrTmp = matchPtn.findall(strings)
    for mst in matchStrTmp:
        lb, sj, nr = '抵扣', deal_dw(mst[1]), deal_dw(mst[0])
        matchStr.append([lb,sj,nr])
    matchStrCnt = len(matchStr)
    matchCs = match_cs(cslist, strings, matchStrCnt)
    for i,ms in enumerate(matchStr):
        try:
            cs = matchCs[i]
        except IndexError:
            cs = ''
        ms.append(cs)
    
    return matchStr
                
def shuangmian(strings):
    '''双免'''
    matchPtn = re.compile('([一二两俩三四五六七八九十\d]+个?[期年月半]{,2})?双免([一二两俩三四五六七八九十\d]+个?[期年月半]{,2})?')
    
    matchCs = []
    matchStr = []
    matchStrTmp = matchPtn.findall(strings)
    for mst in matchStrTmp:
        tmp = mst[0] if mst[0] else mst[1]
        if tmp:
            sj = deal_dw(tmp, dateconver=True)
            lb, nr = '双免', ''
            matchStr.append([lb,sj,nr])
    matchStrCnt = len(matchStr)
    matchCs = match_cs(cslist, strings, matchStrCnt)
    for i,ms in enumerate(matchStr):
        try:
            cs = matchCs[i]
        except IndexError:
            cs = ''
        ms.append(cs)
    
    return matchStr
                
def zhihuan(strings):
    '''置换、换购'''
    ptnList = [        '置换[^置换]{,15}?((?:非?[本同外京全]|其?[他它余]|任[何意]|不限)(?:[品牌]{1,2}|车型))|((?:非?[本同外京全]|其?[他它余]|任[何意]|不限)(?:[品牌]{1,2}|车型))[^置换]{,15}?置换',
        '''
        (
            (?<!综合优惠)(?:\d\.\d{1,2}万
            |[\d一二两俩三四五六七八九十]?[千万][\d一二两俩三四五六七八九十]?
            |\d{4,})元?
        )
        (?:/[台辆])?
        (
            [）\)]?置换礼包
            |(?:置换|换购)(?:专?项?补贴|豪礼|评估[券礼]|政策|折扣|[金礼]|现金|基金)
            |(?:现金|[超至]高|】|的|的不等|金融或|二手车|旧车|厂家|高额|贷款或)(?:置换|换购)补?贴?
            |[（\(]?(?:置换|换购)
        )
        
        |
        
        (置换|换购)[补贴]{,2}[^电话热线]{,20}?
        (?<![\d一二两俩三四五六七八九十])(?:\d{4,}[-—至]{1,})?
        (
            (?:\d\.\d{1,2}万
            |[\d一二两俩三四五六七八九十]?[千万][\d一二两俩三四五六七八九十]?
            |\d{4,}(?!最高|积分))元?
        )
        ''',    ]
    matchPtn = [re.compile(ptn, re.X) for ptn in ptnList]
    flagPtn = re.compile('[外他它余]')
    
    matchCs = []
    matchStr = []
    matchStrTmp = [mp.findall(strings) for mp in matchPtn]
    
    if len(matchStrTmp[0]) == 1 and len(matchStrTmp[1]) > 1:
        jeList = []
        for mst1 in matchStrTmp[1]:
            je = mst1[0] if mst1[0] else mst1[-1]
            je = deal_dw(je).replace('元','')
            jeList.append(je)
        bd = ''.join(matchStrTmp[0][0])
        if flagPtn.search(bd):
            sj = str(min(jeList))+'元'
        else:
            sj = str(max(jeList))+'元'
        nr = deal_brand(bd)
        lb = '置换' if '置换' in matchStrTmp[1][0][1] or '置换' in matchStrTmp[1][0][2] else '换购'
        matchStr.append([lb,sj,nr])
    elif matchStrTmp[1]:
        for i,mst1 in enumerate(matchStrTmp[1]):
            sjtmp = mst1[0] if mst1[0] else mst1[-1]
            sj = deal_dw(sjtmp)
            lb = '置换' if '置换' in mst1[1] or '置换' in mst1[2] else '换购'
            try:
                nr = deal_brand(''.join(matchStrTmp[0][i]))
            except IndexError:
                nr = ''
            matchStr.append([lb,sj,nr])
    
    matchStrCnt = len(matchStr)
    matchCs = match_cs(cslist, strings, matchStrCnt)
    
    for i,ms in enumerate(matchStr):
        try:
            cs = matchCs[i]
        except IndexError:
            cs = ''
        ms.append(cs)
    
    return matchStr
        
def yanbao(strings):
    '''延保、保养、质保'''
    ptnList = [
        '''
        (全系|(?:部分|特定|指定|(?:远行|汽油)版?|机油|混合动力|油电混合|全系|混动)车型|有机会)?
        (?:[可尊更]?享[受有]?【?|的?获得|活动长达|就?送)?
        (发动机(?:变速[器箱])?|机油|电池|涡轮增压器|电芯)?
        (
            (?:[一二两俩三四五六七八九十百首]{1,2}|1?\d|[不无]限)(?:年[限/或内]?|[万公里kmKM]{3}|次)(?:[（\(]?[\d一二两俩三四五六七八九十百首wW不无限]{1,3}(?:[万公里kmKM]{3}|次[）\)]?)|(?:\d{5,}|不限)[公里程]{2}数?|半价|0元)?
            |终[生身](?:免费)?
            |\d+万
        )?的?
        (发动机(?:变速[器箱])?|(?:免费)?机油|电池|涡轮增压器|电芯)?
        (?:超[长级低](?:白金|免费|半价|原厂)?|原厂(?:超长)?|整车|(?:免费?【?|常规|(?:含工时)?基础(?:AB)?|无忧|超长|升级){1,2}|厂家|延长|安心|车主惠享原厂|期送|喜悦|适合您车辆的超值|百万|维修|免费车辆|免费原厂机油和|售后)?
        
        (?:质保|延保|保养|保修|养护)
        
        [礼】（\(限各]{,2}
        (全系|(?:部分|特定|指定|(?:远行|汽油)版?|机油|混合动力|油电混合|全系|混动)车型|有机会)?
        (?:尊?享受?【?|长达|周期为?|延长至|共计|\d{1,2}\-|期限?为|升级|期至)?
        (发动机(?:变速[器箱])?|机油|电池|涡轮增压器|电芯)?
        (
            (?:[一二两俩三四五六七八九十百首]{1,2}|1?\d|[不无]限|\d{4,})(?:年[限/或内]?|[万公里kmKM]{3}|公里|次)(?:[\d一二两俩三四五六七八九十百首wW不无限]{1,3}(?:[万公里kmKM]{3}|次)|(?:\d{4,}|不限)[公里程]{2}数?)?
            |终[生身]
        )?
        ''',
        '(?:质保|延保|保养|保修|养护)+',
    ]
    eptPtn = re.compile('[/或免费]')
    matchPtn = [re.compile(ptn, re.X) for ptn in ptnList]
    
    matchStr = []
    matchStr = []
    matchCs = []
    matchStrTmp = [mp.findall(strings) for mp in matchPtn]
    
    for mst1,mst2 in zip(*matchStrTmp):
        tmp = mst1[2] if mst1[2] else mst1[-1]
        if tmp:
            tmp = eptPtn.sub('',deal_dw(tmp))
            sj = tmp.replace('终身','终生').replace('km','公里').replace('KM','公里')
            nr = ''.join(mst1[0:1]) + ''.join(mst1[3:-1])
            if '质保' in  mst2:
                lb = '质保'
            elif '保养' in mst2:
                lb = '保养'
            elif '保修' in mst2:
                lb = '保修'
            else:
                lb = '延保'
            matchStr.append([lb,sj,nr]) 
            
    matchStrCnt = len(matchStr)
    matchCs = match_cs(cslist, strings, matchStrCnt)
    for i,ms in enumerate(matchStr):
        try:
            cs = matchCs[i]
        except IndexError:
            cs = ''
        ms.append(cs)
    
    return matchStr
        
def baoxiao(strings):
    '''报销'''
    matchPtn = re.compile('报销.*?[费票补]')
    
    matchCs = []
    matchStr = []
    matchStrTmp = matchPtn.findall(strings)

    for mst in matchStrTmp:
        lb, sj, nr= '报销', '报销车费', ''
        matchStr.append([lb,sj,nr])
    matchStrCnt = len(matchStr)
    matchCs = match_cs(cslist, strings, matchStrCnt)
    for i,ms in enumerate(matchStr):
        try:
            cs = matchCs[i]
        except IndexError:
            cs = ''
        ms.append(cs)
    
    return matchStr
        
def shuixian(strings):
    '''税、险'''
    sbPtn = re.compile('(?:[还和]?包含?(?:[保全]?险|(?:购置)?税|上?牌)){3}|(?:[还和]?包(?:[保全]?险|(?:购置)?税|上?牌){2})(?:[还和]?包(?:[保全]?险|(?:购置)?税|上?牌))|(?:[还和]?包(?:[保全]?险|(?:购置)?税|上?牌))(?:[还和]?包(?:[保全]?险|(?:购置)?税|上?牌){2})|(?:[还和]?包(?:[保全]?险|(?:购置)?税|上?牌){3})')
    
    pList = [
        '''
        ([赠送]{1,2}|减[半免]|(?<!避)免(?!息|税)费?办?理?(?!检测)|享受?|省(?!心)|[零抵]|全免|不用交|补贴|免?全额|0)?
        [^享受送免费理省抵贴半额]{,15}?
        (?:盗抢险|0?交强险(?:车船税)?|0?(?<![购买])商业险|全(?:车保|年保)?险|车险|第三者|责任险|三责险|(?:(?:厂家|(?<!CS1)0)?购置|厂家购车|车船(?:使用)?|车购)税)
        [^全含赠送免费办理减免半补贴]{,15}
        (减[半免]|享受?|[赠送]{1,2}|免费办?理?|全免|补贴|半价)?
        ''',
        '''
        (?<!\d{3}\-\d{3}\-)
        (\d{4,}[元\+]?(?:/[台辆])?
            |(?:\d\.?\d?折|\d{1,3}(?:\.\d+)?%|[一二两俩三四五六七八九半]{1,2}[折价])
            |\d\.\d{1,2}[千万]元?
            |(?<!\d)[\d一二两俩三四五六七八九十次首]{1,2}(?:[千万]元?|年)
            |[千万\d]元
        )?[的购]?
        ((?:盗抢险|0?交强险(?:车船税)?|0?(?<![购买])商业险|全(?:车保|年保)?险|车险|第三者|责任险|三责险|(?:(?:厂家|(?<!CS1)0)?购置|厂家购车|车船(?:使用)?|车购)税)(?:补贴(?:优惠)?|(?:厂家)?直补|(?:可享)?国家(?:(?:政策)?补贴)|优惠(?!倒))?)
        (?:优惠倒计时为您节省|(?:最[高多]|可|再)?减免?|年前|可享受?|最高补贴)?
        [可最低高达至再享受劲省减多收取还免]{,2}
        (?:\d{3,}[-—至/]{1,})?
        (\d{4,}[元\+]?(?:/[台辆])?
            |(?:\d\.?\d?折|\d{1,3}(?:\.\d+)?%|[一二两俩三四五六七八九半]{1,2}[折价])
            |\d\.\d{1,2}[千万]元?
            |(?<!\d)[\d一二两俩三四五六七八九十次首]{1,2}(?:[千万]元?|年)
            |[千万\d]元
        )?(?!大礼包|轮胎)
        ''',
    ]
    matchPtn = [re.compile(p, re.X) for p in pList]
    eptPtn1 = re.compile('[最高低至的劲省可享受补贴优惠国家厂家直政策]')
    eptPtn2 = re.compile('[抵减全免费赠送/台辆\+]')
    flagPtn = re.compile('优惠.+|全额|[\d价折千万元年次半零无免送减赠]')
    jePtn = re.compile('(\d{3,})元?')
    numPtn  = re.compile('\d')
    freePtn = re.compile('^0[^\d]')
    
    matchCs = []
    matchStrTmp1 = [mp.findall(strings) for mp in matchPtn]
    matchStrTmp2 = sbPtn.findall(strings)
    matchStr = []
    if matchStrTmp2:
        matchStr = [['包牌包税包保险','',mst2] for mst2 in matchStrTmp2]
    for i,mst11 in enumerate(matchStrTmp1[0]):
        mst11 = ''.join(mst11)
        if any([re.search('[赠送减免交半额]',mst11),    
                flagPtn.search(''.join(chain(*matchStrTmp1[1]))),
                ]):
            try:
                mst12 = matchStrTmp1[1][i]
            except IndexError:
                pass
            else:
                tmp = eptPtn1.sub('',mst11+mst12[0]+mst12[2])
                tmp = eptPtn2.sub('',deal_zk(tmp))
                tmp = jePtn.sub('\\1元',deal_dw(tmp))
                nr = eptPtn1.sub('',mst12[1])
                if numPtn.search(tmp):
                    sj = tmp
                else:
                    sj = ''
                    nr += tmp
                lb = '税' 
                if freePtn.search(nr):
                    sj, nr = '0元', nr[1:]
                if '险' in nr:
                    lb = '险'
                matchStr.append([lb, sj, nr])
                
    matchStrCnt = len(matchStr)
    matchCs = list(set(match_cs(cslist, strings, matchStrCnt)))
    for i,ms in enumerate(matchStr):
        try:
            cs = matchCs[i]
        except IndexError:
            cs = ''
        ms.append(cs)
    
    return matchStr
            
def libao(strings):
    """礼包、礼、奖、油卡、精品、老客户、门票、补贴"""
    ptnList = [
        '''
        ((?:老客户|老车主|公务员|教师|军人|(?:事业单位|[央国]企|知名企业|中石化)(?:员工)?|警官证?|军官证?)*)
        [^老赠送尊受得与公央教取业官]{,15}?
        (?:[赠送]{1,2}|[可尊]?享受?|[获可][得的]?|获赠|可?参与|领取|赢取|免费使用)?
        [^老赠送尊享受得参与取可获①②③]{,10}
        (?:(?:精品(?:内饰)?|(?:原厂)?精[美品][小好]?|豪华?|现金|分期|油卡|(?<!贴息)大|介绍|附件|家电|购车|神秘|进店|售后|签到|老友记|试驾|抽奖|装饰豪?|感恩)大?礼[包品]?|礼[品包物]|精品|红包|(?<!置换)补贴(?![^利息率]{,10}利?[息率])|加?油卡|免费(?:救援|检测|洗车|换)|笔记本|雨伞|(?:购物|会员|月)?卡|娃娃|电影票|套装|手机支架|智能防盗管家系统|机油|数据线|电饭煲|金融手续费|运动衫|(?:行李|旅行箱|烤|登机)箱|金蛋礼|开关金财神|保温杯|太阳眼镜|防爆膜|封釉|地毯|大奖|(?:液晶)?电视|自行车|洗衣机|料理机|电磁炉|电饼铛|微波炉|钥匙扣|金玫瑰|空气净化器|导航|牌照|驾证本|车模|机票|水杯|[家彩]电|邮票|现金(?!优惠))
        (?:免费送|抽取|减免|(?:百分百)?中奖|送不停)?
        ''',
        '''
        (?<!电话)(?<!热线)(?<!专线)
        (
            (?:\d\.\d{1,2}万
            |[\d一二两俩三四五六七八九十百千]?[千万][\d一二两俩三四五六七八九十]?
            |(?<!\d)\d{3,6}
            |\d{1,2}张
            |\d年\d{1,2}桶
            )元?的?
        )?
        (
            (?:现金(?:购车)?|(?:原厂|野外)?(?:安防|露营)|装潢|来斯健身会所|免费配置升级|神秘|轻便|定制|京东|幸运|惊喜|超值|专属(?:试驾)?|厂家(?:原装)?|豪华|保养VIP|全合成|玻璃|提车礼盒|多功能|精美|终身|智能|[新购]车|运动|3D|全车|抛光|原厂|额外|99K|高清大屏|浙A|精致|欧洲任意国家往返|丰厚|限量|滚筒)*
            (?:(?:精品(?:内饰)?|(?:原厂)?精[美品][小好]?|豪华?|抽奖|现金|分期|油卡|(?<!贴息)大|介绍|附件|家电|(?:万元)?购车|神秘|进店|售后|签到|老友记|试驾|装饰豪?|感恩)大?礼[包品]?|礼[品包物]|精品|红包|(?:厂商|公务员|政府|惠民|现金|地方|国家|分期|报废|用电|教师|医生|海归|车改|交通补贴)?(?<!购置税)补贴(?![^利息率]{,10}利?[息率])|加?油卡|免费(?:救援|检测|洗车|换)|笔记本|雨伞|(?:购物|会员|月)?卡|娃娃|电影票|套装|手机支架|防盗管家系统|机油|数据线|电饭煲|金融手续费|运动衫|(?:行李|旅行箱|[冰烤]|登机)箱|金蛋礼|开关金财神|保温杯|太阳眼镜|防爆膜|封釉|地毯|(?:液晶)?电视|自行车|洗衣机|料理机|电磁炉|电饼铛|微波炉|钥匙扣|大奖|金玫瑰|空气净化器|导航|牌照|驾证本|车模|机票|水杯|[家彩]电|邮票|现金(?!优惠))
        )
        (?:免费送|抽取|减免|(?:百分百)?中奖|送不停)?
        (
            (?:\d\.\d{1,2}万|[\d一二两俩三四五六七八九十百]?[千万][\d一二两俩三四五六七八九十]?|\d{3,})元?
            |（.*?(?:）|$)
            |\(.*?\)
        )?
        ''',
    ]
    match1Ptn = [re.compile(ptn,re.X) for ptn in ptnList]
    match2Ptn = re.compile('礼包[A-Z][\(（](\d+元?)[\)）]')
    numPtn = re.compile('\d{3,6}')
    notNumPtn = re.compile('[^\d]')
    splitPtn = re.compile('[\)）]')
    
    matchCs = []
    matchStr = []
    
    if '置换' not in strings and '贴息' not in strings:
        tmp = match2Ptn.findall(strings)
        if tmp:
            lb = '礼包'
            sj = ''.join(tmp).replace('元','') + '元'
            nr = ''.join(splitPtn.split(strings)[1:])
            if nr.startswith('自定义') or '＋' not in nr:
                nr = ''
            matchStr.append([lb, sj, nr])
        else:
            matchStrTmp = [mp.findall(strings) for mp in match1Ptn]
            for i,mst2 in enumerate(matchStrTmp[1]):
                sjtmp = mst2[0] if mst2[0] else mst2[2]
                sjtmp = deal_dw(sjtmp)
                if numPtn.search(sjtmp):
                    sj = notNumPtn.sub('',sjtmp) + '元'
                    try:
                        nr = matchStrTmp[0][i]
                    except IndexError:
                        nr = ''
                    if '油卡' in mst2[1]:
                        lb = '油卡'
                    elif '补贴' in mst2[1]:
                        lb = '补贴'
                        tmp = mst2[1] if len(mst2[1])>2 else ''
                        nr += tmp
                    else:
                        lb = '礼包'
                    matchStr.append([lb, sj, nr])
        matchStrCnt = len(matchStr)
        matchCs = match_cs(cslist, strings, matchStrCnt)
        for i,ms in enumerate(matchStr):
            try:
                cs = matchCs[i]
            except IndexError:
                cs = ''
            ms.append(cs)
    
    return matchStr
                    
if __name__ == '__main__':
    # strings = '购车险再双免2年赠送保养券'
    # print(shuangmian(strings))
    s = '询价就送500元购车抵用券'
    print(dikou(s))
