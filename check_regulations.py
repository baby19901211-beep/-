import os
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import google.generativeai as genai

# 設定區 (從 GitHub Secrets 讀取)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

SAFETY_KEYWORDS = [
    "職業安全衛生", "勞工安全", "設施規則", "作業安全", 
    "高壓氣體", "營造安全", "危險性機械", "有機溶劑", 
    "特定化學物質", "勞工健康", "防護具", "粉塵"
]

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def get_law_updates():
    url = "https://law.moj.gov.tw/News/NewsList.aspx?type=k"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    updates = []
    table = soup.find("table", {"id": "gvList"})
    if not table:
        return []

    rows = table.find_all("tr")[1:]
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 3:
            date_str = cols[0].text.strip()
            title_element = cols[1].find("a")
            if title_element:
                title = title_element.text.strip()
                link = "https://law.moj.gov.tw/News/" + title_element.get("href")
                if any(keyword in title for keyword in SAFETY_KEYWORDS):
                    updates.append({
                        "date": date_str,
                        "title": title,
                        "link": link
                    })
    return updates

def analyze_with_ai(law_item):
    prompt = f"""
    你是一位專業的職業安全衛生管理師與法規專家。
    以下是全國法規資料庫最新發布/修訂的職安相關法規：

    法規名稱/公告：{law_item['title']}
    發布日期：{law_item['date']}
    連結：{law_item['link']}

    請針對這項法規修訂進行分析，並整理成專業的簡報/摘要報告。
    報告請包含以下項目（請使用 HTML 標籤排版，如 <h3>, <ul>, <li>, <strong> 等）：
    1. <strong>修訂背景與主因</strong>：為何進行本次修訂？
    2. <strong>重點修訂內容與條文變更摘要</strong>：有哪些關鍵條文修正？
    3. <strong>對企業/廠區的實務影響與應對建議</strong>：安衛單位、廠區管理人員應配合採取的行動措施。
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"<p>AI 分析失敗：{str(e)}</p>"

def send_email_report(updates_summary_html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "【職安法規月報】全國法規資料庫最新修訂通知"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="background-color: #004085; color: white; padding: 10px 15px; border-radius: 5px;">
           每月職業安全衛生法規修訂與監控報告
        </h2>
        <p>您好，以下是本月為您監控全國法規資料庫中與<b>職業安全衛生</b>相關的最新修訂與整理：</p>
        <hr style="border: 0; border-top: 1px solid #ccc;">
        {updates_summary_html}
        <hr style="border: 0; border-top: 1px solid #ccc;">
        <p style="font-size: 0.85em; color: #777;">本郵件由 GitHub Actions 與 Gemini AI 自動生成與發送。</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.close()
        print("Email 報告已成功發送！")
    except Exception as e:
        print(f"Email 發送失敗：{str(e)}")

if __name__ == "__main__":
    updates = get_law_updates()
    if not updates:
        no_update_html = "<p><strong>本月全國法規資料庫尚無與職業安全衛生相關的新修訂或發布公告。</strong></p>"
        send_email_report(no_update_html)
    else:
        full_report_html = ""
        for idx, item in enumerate(updates[:5], 1):
            ai_summary = analyze_with_ai(item)
            full_report_html += f"""
            <div style="background-color: #f8f9fa; border-left: 4px solid #004085; padding: 15px; margin-bottom: 20px;">
              <h3 style="margin-top:0; color: #004085;">#{idx} {item['title']} ({item['date']})</h3>
              <p><strong>法規連結：</strong> <a href="{item['link']}" target="_blank">{item['link']}</a></p>
              <div>{ai_summary}</div>
            </div>
            """
        send_email_report(full_report_html)
