import akshare as ak
import datetime

stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol="601360", period="daily", start_date="20130301", end_date='20230526', adjust="qfq")
print(stock_zh_a_hist_df)

"""
now = datetime.date.today()
date_hist = ak.tool_trade_date_hist_sina()
date_hist = date_hist.loc[date_hist["trade_date"] <= now]
print(date_hist)

stock_zh_a_index_df = ak.stock_zh_index_daily(symbol="sz399001")
print(stock_zh_a_index_df)

stock_daily = ak.stock_sse_deal_daily()
print(stock_daily)

stocks = ak.stock_info_a_code_name()
print(stocks)
"""
