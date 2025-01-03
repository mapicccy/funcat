import akshare as ak


df = ak.stock_hold_num_cninfo("20220630")
print(df.loc[df["证券代码"] == "002466"])
