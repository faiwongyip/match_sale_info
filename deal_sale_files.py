# -*- coding:utf-8 -*-
import os
import re
import time 
import glob
import multiprocessing
from multiprocessing import Pool
import jieba
import pandas as pd
from match_sale import *

conn250 = pymssql.connect(
    host='<your_host>',
    database='ccpspider',
    user='sa',
    password='<your_password>',
    charset="UTF-8"
)
cur250 = conn250.cursor()

kwfundt = {'贴息': mianxi,'无息': mianxi,'免息': mianxi,
    '0息': mianxi,'零息': mianxi,'券': dikou,'抵': dikou,
    '双免': shuangmian,'置换': zhihuan,'换购': zhihuan,
    '保养': yanbao,'延保': yanbao,'保修': yanbao,
    '质保': yanbao,'礼': libao,'奖': libao,'油卡': libao,
    '精品': libao,'老客户': libao,'门票': libao,
    '补贴': libao,'报销': baoxiao,'险': shuixian,
    '税': shuixian
}   #二级类别对应的函数

funcfydt = {
    mianxi: '金融',dikou: '金融',shuangmian: '金融',
    zhihuan: '置换',yanbao: '延保',baoxiao: '金融',
    shuixian: '其他',libao: '礼包类'
}   #函数对应的一级类别

kwFilename = r'.\match_words.xlsx'
cslist = get_cslist()

def deal_keyword(filename):
    """ 处理match_words.xlsx
        返回关键词列表相关的列表、字典
    """ 
    kwDf = pd.read_excel(filename)
    kwSt = {kw for kw in kwDf['关键词']}
    kwDic = {kw:(cf,re.compile(ctn),re.compile(rm)) if ctn else (cf,ctn,re.compile(rm)) for kw,cf,ctn,rm in zip(kwDf['关键词'],kwDf['类别'],kwDf['包含'].fillna(''),kwDf['排除'])}
    cfIdxDic = {cf:1 for cf in kwDf['类别']}
    firstWdDic = {kw[0]:{'kws':set(),'maxLen':0} for kw in kwDf['关键词']}
    for kw in kwSt:
        if kw[0] in firstWdDic:
            firstWdDic[kw[0]]['kws'].add(kw)
            if len(kw) > firstWdDic[kw[0]]['maxLen']:
                firstWdDic[kw[0]]['maxLen'] = len(kw)
    ptn = '|'.join(kwSt)
    regexCompile = re.compile(ptn)
    return kwSt, kwDic, cfIdxDic, firstWdDic, regexCompile


kwSt, kwDic, cfIdxDic, firstWdDic, regexCompile = deal_keyword(kwFilename)
    
def deal_content(cntfile):
    """ 处理文本文件
        去除无关符号，断句
        返回句子列表
    """
    cntLt = []
    with open(cntfile) as f:
        content = re.sub('(\d)[,，](\d)','\\1\\2',f.read())
        if re.search('\n',content):
            tmpCnt = re.split('[,，。!！?？;；\n]', content)
        else:
            tmpCnt = re.split('[,，。!！?？;；\s]', content)
        cntLt = [re.sub('[\s《》\'’‘:：、"“”]+','',x.strip()) 
                    for x in tmpCnt if x.strip() and len(x.strip())>5]
    return set(cntLt)
    
def match_stc4(regexCompile, stc, kwDic):
    """ 判断关键词在不在句子里
        返回匹配上的关键词列表
    """
    tmpWdLt = regexCompile.findall(stc)
    wdLt = [wd for wd in tmpWdLt if (not kwDic[wd][1] or kwDic[wd][1].search(stc)) and not kwDic[wd][2].search(stc)]
    return set(wdLt)
    
def get_news_info(salesinfoid,postdate,srcsys):
    """ 查询新闻记录信息
    """
    sql = '''
        select brandname,manufacture,city,agencyname,postdate
            ,salesinfoid,carsseriesname,title,srcsys
        from ccpspider.dbo.ccp_xz_newslist_1
        where salesinfoid='%s' and postdate='%s' 
            and srcsys='%s'
    '''
    try:
        cur250.execute(sql % (salesinfoid,postdate,srcsys))
        result = list(cur250.fetchone())
    except Exception as e:
        # print(e)
        result = None
    return result

def insert_data(table, data):
    """ 保存结果插入数据库
    """
    listsql = '''
        insert into saleInfoList        
            (brandname,manufacture,city,agencyname,postdate
                ,salesinfoid,carsseriesname,title,srcsys,flag)
        values ('%s','%s','%s','%s','%s','%s'
                                        ,'%s','%s','%s','%s')
    '''
    cntsql = '''
        insert into saleInfoContent
            (salesinfoid,oneclassify,twoclassify
                ,content,note,mentioncar,srcsys)
        values ('%s','%s','%s','%s','%s','%s','%s')
    '''
    sql = ''
    if table == 'saleInfoList':
        sql = listsql % tuple(data)
    elif table == 'saleInfoContent':
        sql = cntsql % tuple(data)
    else:
        print('表名有误')
        
    try:
        cur250.execute(sql)
    except pymssql.OperationalError as e:
        print('报错！！！','\n',sql)
    except pymssql.IntegrityError as e:
        print('报错！！！','\n',sql,'\n',e)
        return False
    # conn250.commit()
    return True

def close_db():
    cur250.close()
    conn250.close()

def match_from_file(file):
    """
        处理文件，断句，抽取，入库
        数据库有自动去重
        saleInfoList表中salesinfoid与postdate为联合主键
        saleInfoContent表 -- 抽取的结果
        saleInfoList表 -- 新闻基本信息
    """
    salesinfoid = os.path.basename(file).split('.')[0]
    postdate = ''.join(file.split('\\')[-4:-1])
    srcsys = file.split('\\')[-5]
    nextFileflag = False
    insertNewsinfoFlag = True
        
    for stc in deal_content(file):
        if nextFileflag:
            break
        kws = match_stc4(regexCompile, stc, kwDic)
        funs = {kwfundt[kw] for kw in kws}
        for fun in funs:
            if nextFileflag:
                break
            for cnt in fun(stc):
                if insertNewsinfoFlag:
                    # 新闻基本信息只入库一次
                    newsinfo = get_news_info(salesinfoid,postdate,srcsys)
                    if not newsinfo:
                        # 数据库未查询到记录，停止抽取
                        nextFileflag = True
                        break
                    newsinfo = [x if x else '' for x in newsinfo]
                    mentioncar = newsinfo[-2]
                    title = newsinfo[-1]
                    flag = [x for x in ['团购','车展'] if x in title]
                    newsinfo.append(','.join(flag))
                    isInsert = insert_data('saleInfoList', newsinfo)
                    if not isInsert:
                        # 检测到重复值时，停止抽取
                        nextFileflag = True
                        break
                    insertNewsinfoFlag = False
                    
                cnt.insert(0,salesinfoid)
                cnt.insert(1,funcfydt[fun])
                if not cnt[-1]:
                    # 提及车为空时，新闻的车型填充
                    cnt[-1] = mentioncar
                cnt.append(srcsys)
                insert_data('saleInfoContent',cnt)
    conn250.commit()
                        
    
def main():
    """
        主程序
        遍历文件，启动抽取处理
        多进程
    """
    contentDir = [
        r'D:\Crawl\python3\ahnewslist\HTML\AH', 
        r'D:\Crawl\python3\binewslist_redis\newslist_redis\HTML\BI',
    ]   #存放小文件的文件夹
    
    baseDirs = []
    for cDir in contentDir:
        for dir in os.listdir(cDir):
            if dir.startswith('201'):
                baseDirs.append('%s\\%s' % (cDir,dir))
    
    dDirs = []  # 装载每天的文件夹名称
    for baseDir in baseDirs:
        for m in os.listdir(baseDir):
            mDir = os.path.join(baseDir, m)
            for d in os.listdir(mDir):
                dDirs.append(os.path.join(mDir, d))
    
    t1 = time.time()
    pool = Pool(processes=8)    #同时开8个进程
    
    try:
        with open('filefolderFlag.txt') as f:
            filefolderFlag = f.read().strip()
    except FileNotFoundError:
        filefolderFlag = ''
    startFlag = False
    
    for dDir in dDirs:
        print(dDir)
        with open('filefolderFlag.txt','w') as f:
            f.write(dDir)   #记录运行的文件夹
        
        if dDir == filefolderFlag or not filefolderFlag:
            # 从断点文件夹开始运行，标记为空时跑全部文件夹
            startFlag = True
        if startFlag:
            files = []
            for file in glob.iglob('%s\\*.txt' % dDir):
                files.append(file)
            pool.map(match_from_file, files)
        
    pool.close()
    pool.join()
    close_db()
    
    t2 = time.time()
    print('deal_sale_files耗时：',t2-t1)

if __name__ == '__main__':
    main()
