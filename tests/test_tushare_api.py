import tushare as ts
import time

start = time.time()
df = ts.pro_bar(ts_code='300851.SZ', adj='qfq', start_date='20200714', end_date='20200716')
t0 = time.time() - start

print(t0)
print(df)
arr = df.to_records()
start = time.time()
df = ts.get_k_data("603488", start='2020-07-14', end='2020-07-16', index=False, ktype='D', autype='qfq')
t0 = time.time() - start

print(t0)
print(df)
