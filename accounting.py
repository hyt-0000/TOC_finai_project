import datetime
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    HAS_GOOGLE_LIB = True
except ImportError:
    HAS_GOOGLE_LIB = False

# 設定檔名稱
GOOGLE_JSON_FILE = "credentials.json"
SHEET_NAME = "MyFinanceBook"

def write_to_gsheet(item, amount, category="其他雜項"):
    """寫入記帳資料到 Google Sheets (新增分類欄位)"""
    if not HAS_GOOGLE_LIB:
        return "❌ 未安裝 gspread 或 oauth2client 套件"
    
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_FILE, scope)
        client = gspread.authorize(creds)
        
        # 開啟試算表
        sheet = client.open(SHEET_NAME).sheet1
        
        # 準備資料
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 寫入格式調整為：[日期, 分類, 項目, 金額]
        sheet.append_row([date_str, category, item, amount])
        return True

    except FileNotFoundError:
        return "❌ 找不到 credentials.json"
    except Exception as e:
        return f"❌ Google Sheet 錯誤: {str(e)}"

def calculate_category_totals():
    """統計各分類的總金額，並回傳統計結果 (字典)"""
    if not HAS_GOOGLE_LIB:
        return None, "❌ 未安裝 gspread 套件"
    
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        
        # 取得所有資料 (包含標題列)
        rows = sheet.get_all_values()
        
        # 如果只有標題列或沒資料
        if len(rows) <= 1:
            return {}, "⚠️ 目前還沒有記帳資料喔！"
            
        # 統計字典: { "餐飲食品": 500, "交通通勤": 120, ... }
        stats = {}
        
        for row in rows[1:]:
            try:
                # 防呆：確保該行有足夠欄位
                if len(row) < 4: continue
                
                category = row[1] if row[1] else "其他雜項"
                # 將金額轉為整數 (移除可能的空格)
                amount_str = str(row[3]).strip()
                if not amount_str.isdigit(): continue # 如果不是數字就跳過
                
                amount = int(amount_str)
                
                if category in stats:
                    stats[category] += amount
                else:
                    stats[category] = amount
            except:
                continue # 如果這一行有問題，就跳過繼續下一行
                
        return stats, "OK"

    except Exception as e:
        return None, f"❌ 讀取錯誤: {str(e)}"
    
# === 以下是新增的預算管理功能 ===

def get_daily_budget():
    """從 Config 工作表讀取每日預算"""
    if not HAS_GOOGLE_LIB: return 500 # 預設值
    
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_FILE, scope)
        client = gspread.authorize(creds)
        
        # 嘗試開啟 Config 分頁，如果沒有就預設 500
        try:
            config_sheet = client.open(SHEET_NAME).worksheet("Config")
            val = config_sheet.cell(1, 2).value # 讀取 B1
            return int(val) if val else 500
        except:
            return 500
            
    except Exception as e:
        print(f"讀取預算錯誤: {e}")
        return 500

def set_daily_budget(new_budget):
    """更新 Config 工作表的每日預算"""
    if not HAS_GOOGLE_LIB: return "❌ 未連接 Google Sheet"
    
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_FILE, scope)
        client = gspread.authorize(creds)
        
        try:
            config_sheet = client.open(SHEET_NAME).worksheet("Config")
        except:
            # 如果沒有 Config 分頁，就建立一個 
            return "❌ 請先在 Google Sheet 新增一個名為 'Config' 的分頁"

        # 更新 B1 儲存格
        config_sheet.update_cell(1, 2, new_budget) 
        return True
    except Exception as e:
        return f"❌ 設定失敗: {str(e)}"

def get_today_total():
    """計算今天的總消費金額"""
    if not HAS_GOOGLE_LIB: return 0
    
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        
        rows = sheet.get_all_values()
        if len(rows) <= 1: return 0
        
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        total = 0
        
        # 欄位順序: [日期, 分類, 項目, 金額]
        for row in rows[1:]:
            try:
                # 只取前面的日期部分來比對
                row_date = row[0].split(" ")[0] 
                
                if row_date == today_str:
                    amount = int(row[3])
                    total += amount
            except:
                continue
                
        return total
    except Exception as e:
        print(f"計算今日總額錯誤: {e}")
        return 0