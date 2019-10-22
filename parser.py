import csv
import os
import xlsxwriter

def parser():
    """ 整理csv数据
    
    将所有包含企业信息的csv文件数据整理并加载到内存中

    Returns：
        data：整理后的数据格式为：
            data['归属地']['统一社会信用代码'] = ['企业名称', '企业法定代表人', '企业注册属地', '统一社会信用代码']
    """
    input_path = "./data/"

    data = {}
    for filename in os.listdir(input_path):
        with open(os.path.join(input_path, filename), 'r') as fp:
            print(f'正在整理 {filename} 文件。。。')
            for n, row in enumerate(csv.reader(fp)):
                if n == 0:
                    continue
                region, code = row[2].strip(), row[3].strip()
                if region in data:
                    if code not in data[region]:
                        data[region][code] = row
                        # TODO 写入到指定的sheet中
                else:
                    data[region] = {code: row}
                    
    return data
        

def save_to_xlsx(data):
    """ 将数据写入到xlsx文件中
    
    将处理好的数据按照归属地写到对应的sheet中（每个sheet代表一个归属地）

    Params：
        data：已整理好待写入xlsx中的数据
    """
    output_file = 'jzsc.xlsx'
    header = ['企业名称', '企业法定代表人', '企业注册属地', '统一社会信用代码']
    workbook = xlsxwriter.Workbook(output_file)

    for k, v in data.items():
        print(f'正在存储归属地为：{k} 的数据。。。')
        worksheet = workbook.add_worksheet(k)
        for i in range(len(header)):
            worksheet.write(0, i, header[i])
        for i, (_, _v) in enumerate(v.items(), 1):
            for j in range(len(_v)):
                worksheet.write(i, j, _v[j])
    
    workbook.close()


if __name__ == "__main__":
    save_to_xlsx(parser())
