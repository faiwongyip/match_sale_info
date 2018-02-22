# 汽车促销新闻——清洗文本数据

电脑中有监测汽车之家、易车网经销商的促销新闻的txt文件。
读取硬盘中的小文件(大量)，从中解析出金融、延保、礼包、其他类别的关键信息，结果保存在sqlserver中，根据salesinfoid和postdate去重。

## 关键词：
大量小文件、处理文本、正则表达式、多进程

## 结构：
- deal_sale_files.py——处理小文件的主程序
- match_sale.py——抽取类别信息的函数，以及后续处理
- match_words.xlsx——关键词列表
- filefolderFlag.txt——标记处理到的文件夹
- start.bat——启动程序