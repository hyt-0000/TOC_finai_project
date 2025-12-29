import yfinance as yf
import re
import twstock  

# 常用清單 
STOCK_MAP = {
    "台積電": "2330.TW", "鴻海": "2317.TW", "聯發科": "2454.TW",
    "中華電": "2412.TW", "富邦金": "2881.TW", "國泰金": "2882.TW",
    "長榮": "2603.TW", "陽明": "2609.TW", "萬海": "2615.TW",
    "廣達": "2382.TW", "緯創": "3231.TW", "技嘉": "2376.TW",
    "0050": "0050.TW", "0056": "0056.TW", "00878": "00878.TW"
}

def search_stock_code(keyword):
    """
    功能：利用 twstock 套件去搜尋所有台股，找出代碼
    """
    # 1. 如果是原本清單裡有的，直接回傳 
    for name, code in STOCK_MAP.items():
        if name in keyword:
            return code, name

    # 2. 如果清單沒有，使用 twstock 搜尋 
    try:
        # twstock.codes 裡面有全台股的資料
        for code in twstock.codes:
            stock_info = twstock.codes[code]
            # 比對股票名稱是否包含關鍵字 
            if keyword in stock_info.name:
                # 判斷是上市 (.TW) 還是上櫃 (.TWO)
                suffix = ".TWO" if stock_info.market == "上櫃" else ".TW"
                full_code = f"{code}{suffix}"
                return full_code, stock_info.name
    except Exception as e:
        print(f"搜尋代碼錯誤: {e}")

    # 3. 如果是輸入數字 (例如 5201)
    match = re.search(r'\d{4}', keyword)
    if match:
        return match.group() + ".TW", match.group()

    return None, None

def get_stock_price(symbol_code):
    """抓取股價 (這部分不變)"""
    try:
        stock = yf.Ticker(symbol_code)
        df = stock.history(period="6mo")
        if df.empty: return None
        return df['Close']
    except: return None