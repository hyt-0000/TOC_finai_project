import streamlit as st
import re
import pandas as pd
import plotly.express as px
import stock_crawler as stock
import accounting
import ai_advisor

# ==========================================
# 設定區
# ==========================================
LLM_API_KEY = "your_api_key" 

# ==========================================
# 介面設定
# ==========================================
st.set_page_config(page_title="WealthWise AI", layout="wide")
st.title("💰 AI 智慧理財助手")

# 初始化對話紀錄
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "你好！我是你的理財助手。你可以叫我「記帳」，也可以問我「統計」目前的消費狀況喔！"
    })

# ==========================================
# 顯示歷史訊息
# ==========================================
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)
        
        if "chart_data" in msg and msg["chart_data"] is not None:
            unique_key = f"history_chart_{i}"
            if msg.get("chart_type") == "pie":
                st.plotly_chart(msg["chart_data"], key=unique_key)
            elif msg.get("chart_type") == "bar":
                st.bar_chart(msg["chart_data"])
            else:
                st.line_chart(msg["chart_data"])

# ==========================================
# 輔助函式：檢查預算 (共用邏輯)
# ==========================================
def check_budget_status():
    """檢查今日消費是否超過預算，並回傳警示文字"""
    today_total = accounting.get_today_total()
    daily_budget = accounting.get_daily_budget()
    
    msg = ""
    # 如果今日花費超過預算，且預算不是0
    if daily_budget > 0 and today_total > daily_budget:
        over_amount = today_total - daily_budget
        msg = f"""
        <br>
        <div style="background-color: #ffe6e6; padding: 10px; border-radius: 5px; border-left: 5px solid #ff4d4d; color: #cc0000;">
            ⚠️ <b>預算警示：</b> 今日已消費 <b>{today_total}</b> 元<br>
            已超過設定預算 ({daily_budget} 元) 共 <b>{over_amount}</b> 元！💸
        </div>
        """
    return msg

# ==========================================
# 處理使用者輸入
# ==========================================
user_input = st.chat_input("請輸入訊息...")

if user_input:
    # 1. 顯示使用者輸入
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 2. 機器人開始思考
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🤔 處理中...")
        
        response_text = ""
        chart_data = None
        chart_type = "line" 
        
        match_budget = re.search(r"預算\D*?(\d+)", user_input)
        
        if match_budget:
            new_budget = int(match_budget.group(1))
            result = accounting.set_daily_budget(new_budget)
            if result is True:
                response_text = f"✅ <b>設定完成！</b>\n每日預算已更新為：<b>{new_budget}</b> 元"
            else:
                response_text = result

        # --- 邏輯 A: 快速記帳 ---
        elif re.match(r"^(.+)[:：](\d+)$", user_input.replace(" ", "")):
            normalized_input = user_input.replace("：", ":").replace(" ", "")
            match_bookkeeping = re.match(r"^(.+):(\d+)$", normalized_input)
            
            item = match_bookkeeping.group(1)
            amount = int(match_bookkeeping.group(2))
            default_category = "其他雜項"
            
            response_text = f"✅ **快速記帳偵測**\n項目：{item}\n金額：{amount}\n📂 分類：{default_category} (預設)\n"
            write_result = accounting.write_to_gsheet(item, amount, default_category)
            if write_result is True:
                response_text += "💾 已成功寫入 Google Sheet！"
                # 【新增】檢查是否超支
                response_text += check_budget_status()
            else:
                response_text += f"\n⚠️ {write_result}"

        # --- 邏輯 B: 統計分析 ---
        elif any(k in user_input for k in ["算錢", "統計", "分析", "最多", "總結", "計算"]):
            response_text = "📊 **消費統計分析**\n正在讀取您的記帳資料..."
            message_placeholder.markdown(response_text)
            
            stats, status = accounting.calculate_category_totals()
            
            if stats:
                sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
                max_amount = sorted_stats[0][1]
                total_amount = sum(stats.values())
                
                # 取得目前預算資訊顯示在統計裡
                daily_budget = accounting.get_daily_budget()
                
                response_text = f"""
                <div style="font-size: 16px; line-height: 1.8;">
                    <b>📊 本期消費類別明細：</b><br>
                    <hr style="margin: 10px 0;">
                """
                
                for cat, amount in sorted_stats:
                    if amount == max_amount:
                        response_text += f"🏆 <b>{cat}</b>：{amount} 元<br>"
                    else:
                        response_text += f"▫️ {cat}：{amount} 元<br>"
                
                response_text += f"""
                    <hr style="margin: 10px 0;">
                    💰 <b>總支出：{total_amount} 元</b> (每日預算: {daily_budget} 元)
                </div>
                """
                
                df = pd.DataFrame(list(stats.items()), columns=["類別", "金額"])
                fig = px.pie(df, values='金額', names='類別', title='各類別消費佔比', hole=0.3)
                chart_data = fig
                chart_type = "pie"
            else:
                response_text = status

        # --- 邏輯 C: 自然語言記帳 ---
        elif any(k in user_input for k in ["花", "買", "元", "錢", "塊", "吃", "喝"]) or re.search(r'\d+(塊|元)', user_input):
            item, amount, category = ai_advisor.extract_accounting_info(user_input, LLM_API_KEY)
            
            if item and amount and amount > 0:
                response_text = f"🤖 **AI 智慧記帳**\n項目：{item}\n金額：{amount}\n📂 分類：**{category}**\n"
                write_result = accounting.write_to_gsheet(item, amount, category)
                if write_result is True:
                    response_text += "💾 已寫入 Google Sheet。"
                    # 檢查是否超支
                    response_text += check_budget_status()
                else:
                    response_text += f"⚠️ {write_result}"
            else:
                response_text = "🤔 我聽懂你想記帳，但不太確定「項目」或「金額」。\n請試著說：**「買早餐50元」**"

        # --- 邏輯 D: 股票關鍵字查詢 ---
        elif any(k in user_input for k in ["股票", "股價", "走勢", "行情", "了解"]):
            response_text = "🤖 AI 正在分析您的股票需求..."
            message_placeholder.markdown(response_text)
            stock_keyword = ai_advisor.extract_stock_symbol(user_input, LLM_API_KEY)
            
            if stock_keyword:
                response_text = f"✅ AI 偵測到您想查詢：**{stock_keyword}**\n🔍 正在搜尋代碼..."
                message_placeholder.markdown(response_text)
                target_symbol, stock_name = stock.search_stock_code(stock_keyword)
                
                if target_symbol:
                    response_text += f"\n✅ 找到股票：**{stock_name} ({target_symbol})**"
                    chart_data = stock.get_stock_price(target_symbol)
                    if chart_data is not None:
                        last_price = chart_data.iloc[-1]
                        response_text += f"\n📈 最新收盤價：**{last_price:.2f}** 元"
                    else:
                        response_text += "\n⚠️ 抓不到股價資料。"
                else:
                    response_text += "\n⚠️ 找不到這支股票。"
            else:
                response_text = ai_advisor.chat_with_ai(user_input, LLM_API_KEY)

        # --- 邏輯 E: 查股票代碼 ---
        elif "查" in user_input or re.search(r'\d{4}', user_input):
            keyword = user_input.replace("查", "").strip()
            response_text = f"🔍 正在搜尋 **{keyword}** 的代碼..."
            message_placeholder.markdown(response_text)
            target_symbol, stock_name = stock.search_stock_code(keyword)
            
            if target_symbol:
                response_text = f"✅ 找到股票：**{stock_name} ({target_symbol})**\n📉 正在抓取走勢..."
                message_placeholder.markdown(response_text)
                chart_data = stock.get_stock_price(target_symbol)
                if chart_data is not None:
                    last_price = chart_data.iloc[-1]
                    response_text += f"\n📈 最新收盤價：**{last_price:.2f}** 元"
                else:
                    response_text += "\n⚠️ 雖然找到代碼，但抓不到股價數據。"
            else:
                 response_text = ai_advisor.chat_with_ai(user_input, LLM_API_KEY)

        # --- 邏輯 F: 純聊天 ---
        else:
            response_text = ai_advisor.chat_with_ai(user_input, LLM_API_KEY)

        # 3. 顯示結果
        message_placeholder.markdown(response_text, unsafe_allow_html=True)
        
        if chart_data is not None:
            current_key = f"new_chart_{len(st.session_state.messages)}"
            if chart_type == "pie":
                st.plotly_chart(chart_data, key=current_key)
            elif chart_type == "bar":
                st.bar_chart(chart_data)
            else:
                st.line_chart(chart_data)

    # 4. 儲存紀錄
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response_text, 
        "chart_data": chart_data,
        "chart_type": chart_type

    })
