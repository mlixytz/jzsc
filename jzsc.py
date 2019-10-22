import aiohttp
import asyncio
import csv
import json
import random
import re
import requests
import time

from decrypt import AESDecrypt


class JZSC:
    """ 抓取全国建筑市场监管公共服务平台数据
        
        目前可抓取资质信息、地区信息、公司信息
    """

    url = 'http://jzsc.mohurd.gov.cn/api/webApi/dataservice/query/comp/list?pg=%d&pgsz=%d'
    apt_url = "http://jzsc.mohurd.gov.cn/api/webApi/asite/qualapt/aptData"
    region_url = "http://jzsc.mohurd.gov.cn/api/webApi/asite/region/index"
    proxy_url = "http://127.0.0.1:5010"
    file_header = ('企业名称', '企业法定代表人', '企业注册属地', '统一社会信用代码')

    # 每页大小100条
    pgsz = 100

    def __init__(self, start_page=1, end_page=3838):
        """ 设置抓取的起始页和结束页 """
        self.start_page = start_page
        self.end_page = end_page

    def get_region_list(self):
        """ 获取地区信息 
        
        查询地区接口获取全部地区信息，返回值需解密

        Returns: 
            返回地区信息列表，地区信息用元组表示：(地区id, 地区名称)
            例如：
                [('FDFDFCFCFCFC', '北京'), ('FDFEFCFCFCFC', '天津')]
        """
        response = requests.get(self.region_url)
        if not response.ok:
            return []
        data = AESDecrypt.decrypt(response.text)
        return [(item['region_id'], item['region_name']) for item in json.loads(data)['data']['category']['provinces']]

    def get_apt_list(self):
        """ 获取资质信息 
        
        查询资质接口获取全部资质信息，返回值需解密

        Returns: 
            返回地区信息列表，地区信息用元组表示：(资质码, 资质名称)
            例如：
                [('A30904B', '工程设计核工业行业核设施退役及放射性三废处理处置工程专业乙级'), ('A31006B', '工程设计电子通信广电行业电子系统工程专业乙级')]
        
        """
        response = requests.get(self.apt_url)
        if not response.ok:
            return []
        data = AESDecrypt.decrypt(response.text)
        return [(item['APT_CODE'], item['APT_CASENAME']) for item in json.loads(data)['data']['pageList']]

    async def request(self, session, page):
        """ 请求目标页面
        
        真实发起请求，如果请求未成功则删除该代理，并重试，直到抓取到了正确的数据

        Args:
            session: aiohttp.ClientSession() 实例，用来发起请求
            page：要获取的页面

        Returns:
            返回响应中的加密字符串

        """
        # 随机睡1-300秒不等，防止并发太高，对目标网站产生过大压力
        await asyncio.sleep(random.randint(1, 60))
        while True:
            proxy = await self.get_proxy(session)
            try:
                async with session.get(self.url % (page, self.pgsz), proxy=proxy, timeout=30) as response:
                    if response.status == 200:
                        print(f'第{page}页数据已抓取！')
                        return (await response.text(), page)
                    elif response.status == 401:
                        print(f'{page} 系统繁忙。。。')
                        await asyncio.sleep(5)
                    else:
                        await self.delete_proxy(session, proxy)
            except Exception: # 代理异常
                await self.delete_proxy(session, proxy)
        
    async def parse_data(self, enc_str):
        """ 解析数据
        
        解密响应中的加密字符串，并解析成期望的数据格式

        Args:
            enc_str: 响应返回的加密字符串

        Returns:
            返回公司信息列表，公司信息格式：(企业名称, 企业法定代表人, 企业注册属地, 统一社会信用代码)
            例如：
                [('9XXX0702XXXE6U****','浙江**建筑工程有限公司','xxx','浙江省-金华市')]

        """
        try:
            data = json.loads(AESDecrypt.decrypt(enc_str))
        except ValueError:
            return []
        items = data['data']['list']
        ret = []
        for item in items:
            ret.append((item['QY_NAME'], item['QY_FR_NAME'], item['QY_REGION_NAME'], item['QY_ORG_CODE']))
        return ret

    async def fetch(self):
        """ 抓取全部建筑企业信息
        
        按照每页100条，一直抓取到3838页，就可以抓取到全部数据，
        异步抓取，并将返回值存储到指定csv文件中

        """
        async with aiohttp.ClientSession() as session:
            tasks = []
            for page in range(self.start_page, self.end_page+1):
                tasks.append(asyncio.create_task(self.request(session, page)))
            with open(f'data/jzsc_{self.start_page}_{self.end_page}.csv', 'w') as fp:
                writer = csv.writer(fp)
                writer.writerow(self.file_header)
                for task in tasks:
                    enc_str, page = await task
                    items = await self.parse_data(enc_str)
                    if not items: # 如果数据为空，说明抓取错误，则重新抓取
                        tasks.append(asyncio.create_task(self.request(session, page)))
                    for item in items:
                        writer.writerow(item)

    async def get_proxy(self, session):
        async with session.get(f"{self.proxy_url}/get") as response:
            while True:
                try:
                    return json.loads(await response.text())['proxy']
                except KeyError: # 代理池没可用代理时，睡一分钟后重试
                    await asyncio.sleep(60)
    
    async def delete_proxy(self, session, proxy):
        async with session.get(f"{self.proxy_url}/delete?proxy={proxy}"): return


if __name__ == '__main__':
    # 分批抓取，每次抓取100页
    page = 1
    while page < 3839:
        jzsc = JZSC(page, page+99)
        asyncio.run(jzsc.fetch())
        page += 100
        time.sleep(10)
