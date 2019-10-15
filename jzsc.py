import asyncio
import csv
import json
import re
import requests
import time

from lxml import etree


class JZSC:
    url = 'http://jzsc.mohurd.gov.cn/dataservice/query/comp/list'
    apt_url = "http://jzsc.mohurd.gov.cn/asite/qualapt/aptData?apt_type="
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'
    }

    apt_pattern = re.compile('<td.*?apt_code":"(.*?)".*?apt_scope":"(.*?)".*?</td>')

    def get_api_list(self):
        apt_list = []
        
        for i in range(61):
            response = requests.post(self.apt_url, headers=self.headers, data={'$pg': i+1})
            if not response.ok:
                print(f'第{i+1}页资质信息未拿到')
                continue
            apt_list.extend(self.apt_pattern.findall(response.text))
            print(f'第{i+1}页资质信息已拿到')
            time.sleep(1)
        with open('apt.json', 'w', encoding='utf8') as fp:
            json.dump(apt_list, fp)

    def fetch(self):
        apt_lists = []
        with open('apt.json', 'r') as fp:
            apt_lists = json.load(fp)

        regions = []
        with open('region.json', 'r') as fp:
            regions = json.load(fp)

        with open('jzsc.csv', 'w+') as fp:
            writer = csv.writer(fp)
            for region in regions:
                print(f'---------------------正在处理：{region[1]} 地区---------------------')
                for apt_code in apt_lists:
                    print(f'正在处理{region[0]}{region[1]}资质为：{apt_code[0]}{apt_code[1]}的数据')
                    for i in range(30):
                        data = {
                            '$pg': i+1,
                            'apt_code': apt_code[0],
                            'qy_region': region[0],
                        }
                        
                        content = ''
                        while True:
                            proxy = self.get_proxy()
                            try:
                                response = requests.post(self.url, headers=self.headers, data=data, proxies={"http": f'http://{proxy}'}, timeout=15)
                            except requests.RequestException:
                                try:
                                    response = requests.post(self.url, headers=self.headers, data=data, proxies={"https": f'https://{proxy}'}, timeout=15)
                                except requests.RequestException as e:
                                    self.delete_proxy(proxy)
                                    print(f'代理{proxy}不可用, 原因：', e)
                                    continue
                            if not response.ok:
                                print(f'代理{proxy}不可用，状态码：', response.status_code)
                                self.delete_proxy(proxy)
                                continue
                            content = response.text
                            break
                        result = self.parse_jzsc(content)
                        for item in result:
                            print('写入数据', item)
                            writer.writerow(item)

                        if len(result) < 15:
                            break

    async def downloadPages(self):
        apt_lists = []
        with open('apt.json', 'r') as fp:
            apt_lists = json.load(fp)

        regions = []
        with open('region.json', 'r') as fp:
            regions = json.load(fp)

        tasks = []
        for region in regions:
            print(f"正在下载{region[1]}（{region[0]}）的数据")
            for apt_code in apt_lists:
                tasks.append(asyncio.create_task(self.save_page(apt_code, region)))

        for n, task in enumerate(tasks):
            if not n and not n % 610:
                await asyncio.sleep(10)
            await task
            
    def get_content(self, data):
        while True:
            proxy = self.get_proxy()
            try:
                response = requests.post(self.url, headers=self.headers, data=data, proxies={"http": f'http://{proxy}'}, timeout=15)
            except requests.RequestException:
                try:
                    response = requests.post(self.url, headers=self.headers, data=data, proxies={"https": f'https://{proxy}'}, timeout=15)
                except requests.RequestException as e:
                    self.delete_proxy(proxy)
                    continue
            if not response.ok:
                self.delete_proxy(proxy)
                continue
            content = response.text
            return content, "暂未查询到已登记入库信息" not in content

    async def save_page(self, apt_code, region):
        for i in range(30):
            data = {
                '$pg': i+1,
                'apt_code': apt_code[0],
                'qy_region': region[0],
            }
            print(f'正在处理地区为{region[1]}，资质为{apt_code[1]}，第{i+1}页的数据')
            content, has_next = self.get_content(data)
            with open(f'html/{region[1]}_{apt_code[1]}_{i+1}.html', 'w+') as fp:
                fp.write(content)
            
            if not has_next:
                return

    def parse_jzsc(self, text):
        html = etree.HTML(text)
        # 统一社会信用代码
        codes = [item.strip() for item in html.xpath('//td[@data-header="统一社会信用代码"]/text()')]
        # 企业名称
        names = [item.strip() for item in html.xpath('//td[@data-header="企业名称"]/a/text()')]
        # 法人
        entities = [item.strip() for item in html.xpath('//td[@data-header="企业法定代表人"]/text()')]
        # 归属地
        regions = [item.strip() for item in html.xpath('//td[@data-header="企业注册属地"]/text()')]

        return list(zip(codes, names, entities, regions))

    def get_proxy(self):
        content = requests.get("http://127.0.0.1:5010/get/").content
        return json.loads(content)['proxy']
    
    def delete_proxy(self, proxy):
        requests.get(f'http://127.0.0.1:5010/delete/?proxy={proxy}')

jzsc = JZSC()
asyncio.run(jzsc.downloadPages())

# jzsc.get_api_list()
# print(jzsc.get_proxy())