import tushare as ts
import time

df = ts.pro_bar(ts_code='000001.SH', asset="I", start_date='20210701', end_date='20210706')
print(df)
print(df.loc[df["trade_date"] == "20210702"])
print("+++++++++++++++++++++++++++++")
print(df.loc[df["trade_date"] == "20210702"]["pct_chg"].values[0])

print("+++++++++++++++++++++++++++++")

start = time.time()
df = ts.pro_bar(ts_code='300851.SZ', adj='qfq', start_date='20200714', end_date='20200716')
t0 = time.time() - start

print(t0)
print(df)

