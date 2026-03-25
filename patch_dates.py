with open("main.py", "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace(
    '"Profit Ratio" in df_clean.columns, "Missing Profit Ratio column!"',
    '"profit_ratio" in df_clean.columns, "Missing profit_ratio column!"'
)
with open("main.py", "w", encoding="utf-8") as f:
    f.write(c)
print("Fixed main.py assertion")
