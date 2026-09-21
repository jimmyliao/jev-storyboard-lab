FB / Threads post for Day 2 (Traditional Chinese, casual)

---

換個雲端，同一個毛病還是在。

昨天用 Google ADK 生了一支分鏡，Jev 抓到一句話塞不進秒數。今天把同一套邏輯搬到 Microsoft Agent Framework，打 Azure，結果：

7 個片段，1 個被 Jev 標記「唸不完」，而且仔細看完整支影片，其實不只被標記的那段趕，其他幾段也是壓線唸完 😅

順手踩了兩個雲端限定的坑：
→ Azure 官方的 `FoundryChatClient` 只吃 Azure AD 登入，不吃一般 API key（換 `OpenAIChatClient` 才解）
→ Pydantic 的 discriminated union 在 Azure 這邊直接噴 400，Gemini 那邊完全沒事

但最重要的是：Jev 那段檢查邏輯，從昨天到今天一行都沒改。不管分鏡是哪個雲端生的，同一套規則照樣抓得出「格式合法但內容不合理」這件事。

完整文章 + 真實影片：
https://memo.jimmyliao.net/p/jev-microsoft-maf-agent

系列 2/3，明天來處理「怎麼修」。

#GoogleADK #MicrosoftAgentFramework #AIAgents
