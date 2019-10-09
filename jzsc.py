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
                    print(f'正在处理{region[1]}资质为：{apt_code[1]}的数据')
                    time.sleep(.5)
                    for i in range(30):
                        data = {
                            '$pg': i+1,
                            'apt_code': apt_code[0],
                            'qy_region': region[0],
                        }
                        response = requests.post(self.url, headers=self.headers, data=data)
                        if not response.ok:
                            print(f'region：{region[0]}，apt_code：{apt_code[0]}，page：{i+1} 未获取到')
                            continue
                        result = self.parse_jzsc(response.text)
                        if len(result) < 15:
                            break
                        for item in result:
                            writer.writerow(item)
                        time.sleep(.5)


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
        return requests.get("http://127.0.0.1:5010/get/").content

jzsc = JZSC()
# jzsc.fetch()
# jzsc.get_api_list()
print(jzsc.get_proxy())