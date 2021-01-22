import pandas as pd
import requests
import json

from ..utils import get_int_date

url = "https://api.doctorxiong.club/v1/stock?"


def get_runtime_data(ts_code, token=None):
    code_suffix = ts_code[-2:].lower() + ts_code[:-3]

    if token:
        text = requests.get(url + 'code=' + code_suffix + '&token=' + token)
    else:
        text = requests.get(url + 'code=' + code_suffix)

    if text.status_code == 200:
        raw = json.loads(text.text)
        if len(raw['data']) == 0:
            return None
        data = {
            'ts_code': [ts_code],
            'trade_date': [get_int_date(raw['data'][0]['date'][:10])],
            'close': [raw['data'][0]['price']],
            'open': [raw['data'][0]['open']],
            'high': [raw['data'][0]['high']],
            'low': [raw['data'][0]['low']],
            'pre_close': [raw['data'][0]['close']],
            'change': [raw['data'][0]['priceChange']],
            'pct_chg': [raw['data'][0]['changePercent']],
            'vol': [raw['data'][0]['volume']],
            'amount': [float(raw['data'][0]['volume']) * float(raw['data'][0]['price'])],
        }
        df = pd.DataFrame(data)
        return df
    else:
        return None


if __name__ == '__main__':
    get_runtime_data('000001.SZ')
