import streamlit as st
import urllib.request
import urllib.parse
import json
import re

# ==========================================
# 【配置全部交给 Streamlit 界面输入】
# ==========================================
st.set_page_config(page_title="AI 搜索助手", page_icon="🤖", layout="centered")

# 侧边栏配置面板
with st.sidebar:
    st.title("⚙️ API 配置")
    CF_ACCOUNT_ID = st.text_input("Cloudflare Account ID", value="", type="password")
    CF_API_TOKEN = st.text_input("Cloudflare API Token", value="", type="password")
    MODEL = st.text_input("模型", value="@cf/meta/llama-3-8b-instruct")

    st.markdown("---")
    st.title("📚 知识库")
    KB_URL1 = st.text_input("知识库 URL 1", value="https://a.com/1")
    KB_URL2 = st.text_input("知识库 URL 2", value="https://a.com/2")

# ------------------------------
# 清洗 HTML
# ------------------------------
def clean_html(html):
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&[a-z0-9#]+;", " ", html, flags=re.I)
    html = re.sub(r"\s+", " ", html).strip()
    return html[:7000]

# ------------------------------
# 抓取网页
# ------------------------------
def fetch(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as f:
            return clean_html(f.read().decode("utf-8", "ignore"))
    except:
        return ""

# ------------------------------
# 加载知识库
# ------------------------------
@st.cache_data(ttl=3600)
def load_kb(url1, url2):
    return "\n---\n".join([fetch(url1), fetch(url2)])

# ------------------------------
# 搜索
# ------------------------------
@st.cache_data(ttl=60)
def search_web(query):
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
    return fetch(url)

# ------------------------------
# 调用 CF AI
# ------------------------------
def cf_ai(prompt, account_id, api_token, model):
    if not account_id or not api_token:
        return "请先填写 API 配置"
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    try:
        data = json.dumps({"prompt": prompt}).encode()
        req = urllib.request.Request(url, headers=headers, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=20) as f:
            return json.load(f)["result"]["response"].strip()
    except Exception as e:
        return f"AI 调用失败：{str(e)}"

# ------------------------------
# 主逻辑：知识库 → 搜索
# ------------------------------
def agent(query, account_id, api_token, model, kb):
    prompt1 = f"""只用中文回答。
以下是知识库内容：
{kb}

问题：{query}

能回答直接回答，不能只输出：需要联网
"""
    ans = cf_ai(prompt1, account_id, api_token, model)
    if "需要联网" not in ans:
        return "✅ 来自知识库", ans

    web = search_web(query)
    prompt2 = f"""只用中文回答，不编造。
搜索内容：
{web}

问题：{query}
"""
    final = cf_ai(prompt2, account_id, api_token, model)
    return "🌍 来自联网搜索", final

# ==========================================
# 【界面：纯 HTML 聊天 UI】
# ==========================================
st.markdown("""
<style>
.chat-box {
    background:#f7f8fa;
    border-radius:12px;
    padding:20px;
    height:500px;
    overflow-y:auto;
    margin-bottom:16px;
}
.msg-user {
    background:#007bff;
    color:white;
    padding:10px 14px;
    border-radius:8px;
    margin-left:auto;
    max-width:80%;
    margin-bottom:8px;
}
.msg-bot {
    background:#e9ecef;
    padding:10px 14px;
    border-radius:8px;
    max-width:80%;
    margin-bottom:8px;
}
.source {
    font-size:12px;
    color:#666;
    margin-bottom:4px;
}
</style>

<h2 style="text-align:center;">🤖 智能助手（知识库 + 搜索）</h2>
""", unsafe_allow_html=True)

# 输入框
question = st.text_input("输入你的问题：", label_visibility="collapsed", placeholder="请输入问题...")

if st.button("🚀 发送", use_container_width=True):
    if not question:
        st.warning("请输入问题")
    elif not CF_ACCOUNT_ID or not CF_API_TOKEN:
        st.warning("请填写 API 信息（侧边栏）")
    else:
        with st.spinner("处理中..."):
            kb = load_kb(KB_URL1, KB_URL2)
            source, answer = agent(
                question,
                CF_ACCOUNT_ID,
                CF_API_TOKEN,
                MODEL,
                kb
            )

        # 输出 HTML 聊天界面
        st.markdown(f"""
        <div class="chat-box">
            <div class="msg-user">{question}</div>
            <div class="source">{source}</div>
            <div class="msg-bot">{answer}</div>
        </div>
        """, unsafe_allow_html=True)
