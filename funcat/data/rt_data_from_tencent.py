import pandas as pd
import requests
import json


url = "http://qt.gtimg.cn/q="

def get_runtime_data(ts_code, token=None):
    code_suffix = ts_code[-2:].lower() + ts_code[:-3]

    if token:
        text = requests.get(url + code_suffix + '&token=' + token)
    else:
        text = requests.get(url + code_suffix)

    if text.status_code == 200:
        raw = text.text.split("~")
        data = {
            'ts_code': [ts_code],
            'trade_date': [int(raw[30][:8])],
            'close': [float(raw[3])],
            'open': [float(raw[5])],
            'high': [float(raw[33])],
            'low': [float(raw[34])],
            'pre_close': [float(raw[4])],
            'change': [float(raw[31])],
            'pct_chg': [float(raw[32])],
            'vol': [float(raw[36])],
            'amount': [float(raw[37])],
        }
        df = pd.DataFrame(data)
        return df
    else:
        return None


if __name__ == '__main__':
    df = get_runtime_data('601360.SH')
    print(df)
