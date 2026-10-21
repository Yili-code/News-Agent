> 2026-10-21 更正：Founder Morning 已從目前 repository 移除。以下為舊版本歷史記憶；相關路徑、依賴、排程不得作為目前操作指令。

# News Agent 專案記憶

## 2026-10-14 快速導覽（本次原始碼核對）

基準 HEAD：`a95a088`。已閱讀 AGENTS、根目錄／Founder／Social README、CONTRIBUTING、需求文件，並核對核心 Python、Worker、資料儲存、依賴與五份 workflow。以下為靜態檢閱結果；下方 2026-10-07 的測試紀錄保留原日期，不代表本次重新執行。

- **架構與入口：** `news_agent.py` 完成六個 RSS 的擷取、過濾、十筆歷史去重、Gemini 英文摘要及 Telegram 發送；`qa_agent.py` 長輪詢指定 chat，重用同一 runner。`social/pipeline.py` 也重用 NewsFetcher／AgentBrain，但選題不寫回新聞歷史。修改共用程式需同時考慮這三個呼叫端。
- **Founder：** `founder/pipeline.py` 用標準函式庫收集 HN、Product Hunt、DEV，依回饋與新鮮度選最多三筆；`founder/app.py` 提供 Flask API、登入和原生前端，Vertex AI 分析失敗保留 `source_only`。`founder/storage.py` 依 GOOGLE_CLOUD_PROJECT 選 Firestore 或本機 SQLite。Cloud Run Docker 使用 Python 3.12、gunicorn；資料結構見 `founder/migrations/0001.sql`。
- **Social：** Python 選題 → Worker 問真實反應 → Workers AI 最多追問一次或產生兩平台草稿 → Telegram 明確批准 → 分平台發布。D1 schema 在 `social/migrations/0001.sql`；`unknown`／`publishing`／`published` receipt 阻止自動重送。這是獨立 Cloudflare 部署，不沿用 Founder 的 Cloud Run 設定。
- **依賴與慣例：** 根目錄固定 google-genai、requests、feedparser、python-dotenv 版本；Founder 另有 Flask、Firestore、gunicorn、tzdata。Social Worker 無 npm 專案，測試使用 Node 24。從 repo 根目錄執行指令，新聞及 Q&A 狀態檔使用相對路徑。修改保持聚焦；來源事實、模型推論與待驗證需求分開記錄，不把私人資料或憑證提交。
- **常用驗證：** 安裝 `python -m pip install -r requirements.txt -r founder/requirements.txt pytest`；完整 Python 驗證用 `python -m pytest -p no:cacheprovider -q`；Worker 用 `node --check social/worker.mjs` 及 `node --test social/tests/worker.test.mjs`。根 README／CONTRIBUTING 的 `python -m unittest -v` 不足以涵蓋 Founder。CI 分別使用 Python 3.11／3.12 與 Node 24。
- **排程設定（台灣）：** 新聞 08:00／16:00；Q&A 每 20 分鐘；Founder 05:37 準備、06:07 發送、06:37 補跑；Social 07:30。後兩者需對應 ENABLED variable 為 `true`。設定存在不代表線上已啟用或準時送達。
- **操作注意：** 正式新聞／Q&A 入口會發訊息；Social `--dry-run` 仍呼叫 RSS 與 Gemini。Founder `--local-output` 仍擷取公開來源，若已有遠端 URL／token 也可能呼叫遠端分析；import Founder app 會初始化 store。新聞先存歷史再發送；Q&A offset 先存再處理，且 Actions 不保存更新後 offset。Founder 同日已存在 issue 只检查 delivery，不補分析。
- **待確認：** 本次未執行測試或正式入口，未驗證雲端部署、排程啟用、模型可用性、OAuth 權限、token 續期、真實發文或費用。既有記憶列出的併發風險與 Firestore 前端契約問題未在本次重現；仍應另測。需求文件中的 Workers/D1 Founder 架構是舊提案，現況以程式及 Founder README 為準。

以下保留先前詳細導覽與檢查紀錄。

更新日期：2026-10-07，Asia/Taipei。程式基準：`a95a088`；最近功能變更為 `4f2727f`。這個 repo 是 YiLi 的單人資訊與研究工具，包含三個獨立交付流程。後續工作應先辨識要改哪個流程，避免混用部署、憑證與狀態。

## 產品方向

| 流程 | 目的與語言 | 主要入口 | 執行與持久化 |
| --- | --- | --- | --- |
| News Agent | 每次一則有技術深度及創業啟發的英文 brief，提示要求 120–180 個英文單字 | `news_agent.py`；`qa_agent.py` 可觸發同一流程 | GitHub Actions、Gemini API、Telegram；repo 中的 JSON 歷史 |
| Founder Morning 拾題 | 中文市場線索、創業判斷與私人研究筆記；每日 15 分鐘、週日 30 分鐘 | `founder/pipeline.py`、`founder/app.py` | Cloud Run、Vertex AI、Firestore；本機 SQLite |
| Private Social Editor | 先取得 YiLi 的真實反應，再產生 Threads 與 LinkedIn 個別草稿 | `social/pipeline.py`、`social/worker.mjs` | Actions 選題；Cloudflare Worker、Workers AI、D1、Telegram webhook |

`docs/founder-discovery-requirements.md` 記錄的使用者需求是：全球市場、領域保持開放、依明確回饋學習、保留陌生主題、三個月內探索值得投入的題目。文件中的零預算目標是需求，不代表目前 Google Cloud 架構已證明可以永久免費。

共同內容原則是少量、有用、可追溯；不把新聞熱度、融資、產品宣傳視為需求或付費證據。Founder Morning 最近加入 `ACT`、`SAVE`、`SKIP`，重點是讓使用者知道今天是否值得行動，不是增加待讀連結。

## 新聞摘要與 Q&A

`NewsFetcher.fetch_news()` 依序讀取六個 RSS 來源：arXiv cs.CL、The Information、TechCrunch AI、TechCrunch Startups、VentureBeat AI、InfoQ。每個來源最多三筆，使用 RSS 標題、網址、摘要，摘要去 HTML 後截到 500 字元，沒有抓全文。單一來源失敗仍繼續；純硬體關鍵字且缺乏軟體或 AI 脈絡時略過。

`AgentBrain.dedupe_news_items()` 先做本批精確 key 去重，再比對歷史網址及正規化標題／摘要，包含子字串與 `SequenceMatcher >= 0.8`。歷史只保留十筆，每筆報告摘要最多前 200 字元，可另含選定來源資料。舊格式字串歷史也能讀取；損壞 JSON 會被改名備份。檔案路徑相對目前工作目錄，執行時應在 repo 根目錄。

`generate_daily_report()` 選一篇、生成 Telegram HTML，從輸出中的連結嘗試對回來源，然後儲存歷史。提示要求 What happened、Technical core、Founder perspective、Why this matters to me，One action today 可省略。字數、來源連結與事實性主要依提示約束，並非完整程式驗證。

目前新聞與 Q&A 程式寫死的模型字串均為 `gemini-3.5-flash-lite`；這是程式設定，並非已驗證服務可用性。根目錄 `load_dotenv(override=True)` 在 import 時讀設定，會覆蓋同名既有環境值。需要 `GEMINI_API_KEY`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`。

`run_news_agent()` 的順序是擷取 → 生成及寫入歷史 → 發送 Telegram。回傳 bool；無內容與發送失敗都可能是 False。`send_telegram_message()` 在 API 回覆 `ok=false` 時移除 HTML parse mode 再試一次，但不會清除原文字串的 HTML 標籤。

`qa_agent.py` 是指定 chat 的長輪詢介面：忽略 bot 與其他 chat，Gemini 判定 `TRIGGER_NEWS` 或 `GENERAL_CHAT`，以繁體中文 JARVIS 口吻回覆。news runner 成功時已自行發送，Q&A 不應再發一次簡報。update offset 在處理訊息前寫到本機 JSON；Hosted workflow 不保存 offset 或此次新聞歷史變更，不能宣稱 durable 或 exactly-once。

## Founder Morning

`founder/pipeline.py` 僅用 Python 標準函式庫做蒐集與服務呼叫。來源為 HN Ask／Show、Product Hunt Atom、DEV 公開 API；HN 候選最多各十筆，選中後最多補三則直接留言。日報日期使用台灣時區，優先過濾已出現在 context 的 id、超過七天的已知日期與本批相同正規化標題。

偏好權重為 interested +1、research +2、skip -1，排序權重截在 -4 到 +4，再用日期與 id 雜湊打散。同批前兩筆盡量來自不同來源，第三筆從剩餘資料挑較陌生主題。週日或 `--weekly` 從近期 issues 與回饋挑同主題最多三筆；完全沒有選中資料時退回日常選題。去重 context 是最近八期，不是全部歷史。

遠端流程：GET `/internal/context` → 蒐集及選題 → POST `/internal/analyze` → POST `/internal/issues` → 有 `--send` 時 POST `/internal/deliver`。內部端點使用 Bearer `JOB_TOKEN`，Actions 對應 `FOUNDER_JOB_TOKEN`。網站的 session 與 job token 分開，job token 本身不能當瀏覽器 session。

`founder/app.py` 是 Flask API 與靜態網頁入口；`founder/storage.py` 提供兩個 store。設定 `GOOGLE_CLOUD_PROJECT` 就使用指定 named Firestore database，預設名 `founder-morning`；否則建立 `founder/.local/state.sqlite3`。import app 本身便會初始化 store；測試前要確認沒有意外指向雲端的環境設定。

AI 使用 Vertex AI，預設 `gemini-2.5-flash`、location `global`，可由 `AI_MODEL`、`VERTEX_LOCATION` 覆寫。`valid_analysis()` 檢查必要欄位、卡片 id、決策列舉及 evidence ids 必須屬於本批。AI 預算每天最多六次，以 UTC 日期計數，和日報的台灣日期不同。提示要求每天最多一個 ACT，但 validator 沒有檢查 ACT 數量。失敗保留 `source_only`；沒有候選是 `empty`，成功是 `analyzed`。

網站為原生 HTML／CSS／JavaScript，沒有框架或打包工具。`founder/public/app.js` 以 hash 切換今日、候選題目、每週研究、探索偏好。偏好、收藏與筆記寫入後端，輸入中的筆記暫存在瀏覽器 Map。風格為米白、深綠、襯線中文標題，保留現有視覺方向即可。

`/api/login` 使用 `APP_KEY`，發出 30 天 HttpOnly、SameSite Strict session，後端只存 token hash；HTTPS 時 cookie 設 Secure。登出會撤銷 session。登入依 IP 計次並限流，跨 origin 寫入拒絕；`/api/state`、`/api/feedback` 需要 session。資料表／collections 為 sessions、login_attempts、issues、signals、feedback、deliveries、ai_budget。state 回最近 90 期、最近七筆 delivery 與所有回饋；沒有完整自動清理政策。

Telegram 用日期 claim delivery，先記 `sending`，成功為 `sent`，不確定為 `unknown`；429 釋放 claim 並回傳 retry_after。其他失敗通常留下 claim，後續回 `already_claimed`，應先確認是否送達再處理。SQLite 使用 lock 與唯一 key；Firestore 的 AI budget、delivery claim 使用 transaction。這不等於外部服務 exactly-once。

本機預覽：安裝 `founder/requirements.txt`，執行 `python founder/pipeline.py --local-output founder/.local/issue.json`，再 `python founder/app.py`，網址 `http://127.0.0.1:8787`，本機預設登入碼 `morning-local`。本機輸出仍會讀公開來源；若環境另設 FOUNDER_URL 與 token，pipeline 仍可能呼叫遠端 context／AI。

## Social Editor

`social/pipeline.py` 重用 NewsFetcher 與 AgentBrain 的新聞歷史去重，只接受具 HTTPS URL、標題與摘要的候選。Gemini 回 JSON，可用 selected_number=0 跳過；選中來源保留原始 metadata，再加中文事實摘要與兩個具體問題。candidate id 是來源網址的 SHA-256 前 24 位。此流程不把選題寫回 news_history。

POST `/internal/candidates` 使用 Worker `JOB_TOKEN`。Worker 驗證來源欄位，D1 依 candidate id 去重；有活躍對話回 `busy`，下一個新候選到來時才將超過 20 小時未更新的活躍對話過期。

主要狀態：queued → awaiting_response → awaiting_followup 或 draft_ready → awaiting_revision 或發布。也可 skipped、expired；問題送達不確定會成 question_delivery_unknown。發布結果為 published、partially_published、publication_incomplete，並且 `publications` 依 candidate_id 與 platform 分別保存 publishing／published／failed／unknown 與 remote id。

Telegram webhook 必須有 `TELEGRAM_WEBHOOK_SECRET` 且 chat 符合 `TELEGRAM_OWNER_CHAT_ID`。update id 先以 `processed_updates` claim；正式 Worker 用 waitUntil 在背景處理。只支援文字回覆，明確「無感／跳過」可直接略過。Workers AI 最多追問一次，可決定跳過或產生兩個草稿；Threads 上限 500 字元，LinkedIn 1600 字元。

Telegram 按鈕可批准兩邊、單一平台、要求修改或跳過。只有批准路徑呼叫 publisher；Threads 先建 container 再 publish，LinkedIn 使用 REST posts。published、unknown、publishing 的 platform receipt 不會自動再次發送。OAuth 權限、token 續期與 LinkedIn API version 需另行驗證；範例設定的 LINKEDIN_VERSION 是占位值。

Worker 無 npm 依賴；測試用 Node 24 的 `node:sqlite` 模擬 D1，fetch 與 AI 被 mock。`--dry-run` 只阻止送候選給 Worker，仍會呼叫 RSS 與 Gemini。

## 排程與部署

以下是 repo 內設定，並非已確認線上啟用狀態。GitHub cron 使用 UTC，台灣時刻如下。

| Workflow | 台灣時刻或觸發 | 特別行為 |
| --- | --- | --- |
| `ci.yml` | main push、PR | Python 3.11 完整 pytest；3.12 Founder unittest；Node 24 Social tests |
| `daily_news.yml` | 每日 08:00、16:00；可手動 | 可寫 contents，成功流程後 commit news_history，沒有 concurrency 群組 |
| `qa_check.yml` | 每 20 分鐘；可手動 | 長輪詢最長 20 分鐘，新 run 可取消舊 run；offset 不持久化 |
| `founder_morning.yml` | 05:37 準備、06:07 發送、06:37 補跑 | `FOUNDER_ENABLED == 'true'` 才跑；獨立 concurrency |
| `social_editor.yml` | 每日 07:30；可手動 | `SOCIAL_EDITOR_ENABLED == 'true'` 才跑；獨立 concurrency |

Founder Cloud Run 用 `founder/Dockerfile`，Python 3.12、gunicorn 一個 worker／八個 threads，PORT 預設 8080。README 的 Google Cloud project 是部署範例；不能僅據此認定目前資源存在。Secret Manager secrets 對應 APP_KEY、JOB_TOKEN 與專用 Telegram 設定，與新聞摘要及 Social Editor 分離。

## 驗證方式

依賴分為根目錄 `requirements.txt` 與 `founder/requirements.txt`，pytest 由 CI 額外安裝。Social Worker 測試不需 npm install。

```text
python -m pip install -r requirements.txt -r founder/requirements.txt pytest
python -m pytest -p no:cacheprovider -q
python -m unittest discover -s founder/tests -p "test_*.py"
python -m py_compile news_agent.py qa_agent.py test_news_agent.py
node --check social/worker.mjs
node --test social/tests/worker.test.mjs
```

測試分布：`test_news_agent.py` 四項、`test_social_pipeline.py` 五項、`founder/tests` 十二項、Social Worker 九項。根目錄 `python -m unittest -v` 不會完整涵蓋 founder/tests，完整 Python 驗證以 pytest 為準。Q&A 無專屬測試檔，Firestore 也沒有真實後端整合測試。

2026-10-07 本機檢查：已建立被 git 忽略的 `.venv` 並安裝兩份 requirements 與 pytest；使用 Python 3.13.5 執行 `./.venv/Scripts/python.exe -m pytest -p no:cacheprovider -q`，21 項通過。Node 24.14.0 的 Worker 九項測試通過，合計 30 項；Worker、前端 JavaScript 語法檢查與上述 Python 編譯檢查也通過。系統 Python 原本缺少 feedparser 與 google.genai，後續請使用此隔離環境。這次本機 Python 版本不同於 CI 的 3.11／3.12；測試也不代表 RSS、Gemini、Cloud Run、Firestore、Telegram 或真實社群帳號已完成線上驗證。

## 後續工作要留意的差異

以下是程式觀察與局部驗證所得，並非本次已修復的項目。

1. **新聞送達與去重分離。** 歷史先寫，Telegram 後送；送達失敗的新聞可能已被去重。日期用主機本地 datetime，不是明確台灣日期。main 忽略回傳 False，故部分失敗可仍以 process exit 0 結束。
2. **Founder 分析補跑缺口。** 同日 issue 已存在就只檢查 delivery，不補做 source_only 的分析；以 mock context 重現後只發出 context 請求。儲存也以保留首份 issue 為主；要做重分析需一起考慮 pipeline 與 store 行為。
3. **兩種 store 的前端契約不同。** SQLite feedback.body 是 JSON 字串，Firestore feedback.body 是物件；前端 allSignals 對未包含在最近 issues 的回饋一律 JSON.parse。抽取現有 allSignals 函式，以兩種資料形狀局部驗證：SQLite 正常，Firestore 形狀觸發 SyntaxError。此問題會影響不在最近 issues 中的舊收藏；尚未在真實 Firestore 部署重現，既有 SQLite 測試不涵蓋此路徑。
4. **Cloudflare 遺留檔不是 Flask 設定。** `founder/public/_headers` 不會被 Flask 自動套用；本機 test client 確認回應沒有該檔宣告的 CSP、X-Frame-Options、Referrer-Policy。`docs/founder-discovery-requirements.md` 仍描述舊 Workers/D1 架構，現況以 founder README、程式與 Dockerfile 為準。
5. **Social 的順序測試不代表併發安全。** 現有測試驗證逐次 callback；publication 的查詢再寫入、active conversation 的查詢再新增沒有原子 claim。併發 webhook 的重複發布／多活躍對話風險仍需另測。按鈕僅綁 candidate id，不綁草稿版本。
6. **Social 完成後的操作受限。** 發布後 candidate 離開可操作狀態；只批准一個平台後不能直接靠舊按鈕再批准另一個。partial／incomplete 也缺少一般重試入口。維護時不要把 receipt 的去重能力誤認成完整復原流程。
7. **本機設定排除不完整。** social README 要求 wrangler.toml 保持本機，但現有 ignore 只排除 .dev.vars 與 .wrangler，`social/wrangler.toml` 未被忽略。提交前應確認沒有把本機設定帶入。
8. **測試狀態隔離有限。** 新聞測試用固定的系統暫存 `news_history_test.json` 且會寫檔，沒有 teardown；重跑或併發測試出現異常時先檢查該狀態，不要立即歸咎正式流程。

## 維護慣例

遵循 `CONTRIBUTING.md`，變更保持聚焦，說明使用者問題、行為、驗證與成本／排程／隱私影響。需求是理解與儲存記憶時，不順便部署、啟用排程或發送真實訊息。機密值與私人研究資料不進入這份記憶。repo 尚未選定開源授權；不要因公開可見就宣稱可自由重用。
