FB / Threads post for Day 3 (Traditional Chinese, casual)

---

Jev 抓到問題之後，然後呢？

前兩天證明了 Jev 能抓出「文字塞不進影片秒數」這個問題，不管分鏡是 Google ADK 還是 Microsoft Agent Framework 生的。但「抓到」只是第一步，怎麼修才是真正要做決定的地方。

同一段被標記的文案，我試了兩種修法：
→ 修法 A：文字砍短，秒數不變（規格可攜，2s，confidence 0.70→0.53）
→ 修法 B：文字不動，秒數拉長（一份規格，兩套雲端。追蹤看完整實作，2s→5s，confidence 0.70→0.43）

這次沒有隨便信 Jev 的分數就收工，另外拿真的語音辨識（本地跑 faster-whisper，不是丟給 LLM 用文字猜）逐一驗證：原版真的沒講完，修法 B 真的把整句講完、還留了緩衝。

兩種修法都合法，但選哪個是產品決策，不是 Jev 能幫你決定的——這正是這三天系列最後想講的事。

完整文章：
https://memo.jimmyliao.net/p/jev-microsoft-maf-agent

（連結之後補上 Day3 正式發布網址）

系列 3/3，全部程式碼跟真實測試結果都在 repo 裡。

#GoogleADK #MicrosoftAgentFramework #AIAgents
