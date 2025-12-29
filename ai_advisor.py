import requests
import json

# 設定 API 資訊
LLM_API_URL = "https://api-gateway.netdb.csie.ncku.edu.tw/api/generate"
MODEL_NAME = "gemma3:4b"

def call_ncku_llm(prompt, api_key):
    """呼叫 NCKU 的 Gemma 模型"""
    headers = {
        "Authorization": f"Bearer {api_key}", 
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME, 
        "prompt": prompt, 
        "stream": False, 
        "format": "json" # 這裡預設強制 JSON
    }
    
    try:
        response = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=120)
        
        if response.status_code == 200:
            return response.json().get('response', '')
        elif response.status_code == 403:
            return "Error 403: 權限不足 (檢查 API Key)"
        else:
            return f"Error {response.status_code}"
    except Exception as e:
        return f"連線錯誤: {str(e)}"

def extract_accounting_info(user_input, api_key):
    """專門用來提取記帳資訊的 AI 函數 (包含自動分類)"""
    
    categories = [
        "餐飲食品", "交通通勤", "生活用品", "娛樂休閒", 
        "醫療保健", "學習進修", "美妝服飾", "其他雜項"
    ]
    
    # 在 Prompt 裡增加「口語規則」
    prompt = f"""
    你是一個記帳助手。請從這句話提取「項目」、「金額」並自動判斷「分類」。
    
    可用的分類清單：{categories}
    
    規則：
    1. 即使句子沒有動詞（例如 "買"、"花"），只要有「物品」和「金額」，就視為消費。
    2. 範例："30塊的筆" -> {{"item": "筆", "amount": 30, "category": "生活用品"}}
    3. 範例："吃2000" -> {{"item": "餐飲", "amount": 2000, "category": "餐飲食品"}}
    4. 如果使用者「沒有提到具體數字」，amount 請務必回傳 0。
    5. 回傳格式必須是純 JSON。
    
    使用者輸入：{user_input}
    """

    response = call_ncku_llm(prompt, api_key)
    
    try:
        data = json.loads(response)
        return data.get("item"), data.get("amount", 0), data.get("category", "其他雜項")
    except:
        return None, 0, "其他雜項"

def chat_with_ai(user_input, api_key):
    """一般聊天模式"""
    # 用 prompt 引導它回傳內容字串
    prompt = f"你是一個繁體中文助手。請簡短回應：{user_input}。請直接回傳內容字串。"
    return call_ncku_llm(prompt, api_key)

def extract_stock_symbol(user_input, api_key):
    """
    讓 AI 從自然語言中提取股票名稱
    例如："我想了解凱崴股票" -> 回傳 "凱崴"
    """
    prompt = f"""
    你是一個金融助手。請分析使用者輸入的句子：'{user_input}'。
    1. 如果使用者想查詢某支股票，請提取出「股票名稱」或「代碼」。
    2. 回傳格式必須是純 JSON，格式為：{{"stock": "股票名稱"}}。
    3. 如果這句話沒有在問股票，請回傳 {{"stock": null}}。
    
    範例：
    "我想看台積電" -> {{"stock": "台積電"}}
    "凱崴的走勢如何" -> {{"stock": "凱崴"}}
    "你好嗎" -> {{"stock": null}}
    """
    
    response = call_ncku_llm(prompt, api_key)
    
    try:
        # 嘗試解析 JSON
        data = json.loads(response)
        return data.get("stock")
    except:
        # 如果 AI 回傳格式爛掉，就當作沒抓到
        return None