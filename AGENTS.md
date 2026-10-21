<!-- BEGIN CODEX CROSS-SESSION SYNC -->
## 多對話與跨電腦交接（2026-10-21）

這一節是目前的交接規則；下方有日期的舊摘要保留作歷史導覽，不能當成目前進度。使用者最新明確指示優先。

### 每次開始或恢復工作
- 先確認本次 SessionStart / UserPromptSubmit hook 的同步結果。若未執行，從專案根目錄執行 `python .codex/session_sync.py --manual`（macOS/Linux 可用 python3）。
- hook 只 fetch 並在工作目錄乾淨且歷史可快轉時更新追蹤分支。不會 commit、push、stash、reset 或覆蓋衝突。
- 同步失敗、遠端領先且本機有修改、歷史分歧時，先處理同步問題；可做唯讀診斷，不可把狀態說成已同步。離線工作需明確標記。
- 同步後重新讀取本檔、PROJECT_STATUS.md、相關 docs/handoffs/ 紀錄，再核對實際檔案、近期提交與未提交修改。不要單憑聊天記憶重做已完成的功能。
- 實作以檔案與驗證為準；需求以最新明確指示為準；記錄衝突要指出，不臆測完成。歷史摘要中的測試與部署結果不適用於新版本。

### 每個任務自動留下紀錄
- 開始實作時建立獨立 `docs/handoffs/<日期>-<任務>-<唯一識別>.md`，記錄工作範圍、分支與涉及檔案；先查看其他 active 任務，避免重疊編輯。
- 在重要決策、可驗證階段完成，以及每次有實質進展的最終回覆前更新自己的紀錄，不需使用者另貼同步指令。
- 記錄含時區的更新時間、基準提交、目標、已實作/已驗證/未完成、取消的方案、驗證結果、下一步、commit/push 狀態。不可把中斷工作標成完成。
- PROJECT_STATUS.md 只放共同目標、穩定決策與交接目錄入口；詳細進度分散於各任務檔。修改共用文件前重讀，保留他人更新。
- 完成可交接工作時，檢查並只提交本任務相關且可分享的檔案，連同交接紀錄；沿用既有分支/PR 流程並推送已設定的遠端。若含其他任務未發布提交、未解決衝突或無法驗證內容，先回報，不能盲目全部加入。
- 不提交秘密、私人資料、原始聊天或無關修改；不 force push、不自動丟棄修改。雲端程式部署與 Git 同步不同，未另獲授權不執行部署。

### 自動化限制
- `.codex/hooks.json` 設定新建、恢復、分叉、壓縮後及每次新提示的同步檢查；需要本機 Codex 支援、Python 3、Git、遠端存取及專案/hook 信任。
- 新或變更的 hook 需要使用者在 Codex 的 hook 審查介面信任；CLI 可使用 `/hooks`。不得自行修改信任紀錄或繞過審查。
- 其他電腦必須先取得這些檔案並信任 hook。已開啟的聊天應重新讀取指引，不能假設即時載入。
- 檔案規則與同步鎖不是跨對話編輯鎖。多任務重疊時使用獨立分支/worktree，並明確整合。
<!-- END CODEX CROSS-SESSION SYNC -->


## 歷史專案導覽（使用前核對目前程式）

# 專案工作記憶

開始處理這個 repo 時，先讀取 [docs/repo-memory.md](docs/repo-memory.md)，再閱讀相關模組的 README 與實作。記憶是有日期的導覽，不取代目前程式或使用者的新指示。

## 專案界線

- 這是 YiLi 的單人使用專案，目前包含英文新聞摘要與 Private Social Editor；Founder Morning 已在遠端移除，舊記憶中的 Founder 段落僅供歷史參考。
- `news_agent.py` 與 `qa_agent.py` 共用新聞摘要流程；`social/pipeline.py` 重用新聞擷取與去重。修改共用部分時要考慮這些呼叫端。
- Social Editor 使用 Cloudflare Worker、D1、Workers AI；Founder Morning 程式與 workflow 已移除，不應依舊記憶重建。
- 保留來源事實、模型推論與待驗證假設的區別，不杜撰使用者經驗、付費意願或需求證據。
- Social Editor 必須保留 Telegram 明確批准後才發布的行為；沒回覆不發布，`unknown` 不自動重送，各平台結果分別記錄。
- 憑證、私人筆記與完整 Telegram payload 不寫入版本控制。研究或測試時不要直接執行會發送訊息的正式入口。

## 驗證入口

Python 完整測試是 `python -m pytest -p no:cacheprovider -q`，需根目錄 requirements.txt 的依賴與 pytest；已移除的 founder/requirements.txt 不再適用；根目錄的 `unittest` 預設探索不足以代表全部測試。

Social Worker 使用 Node 24：`node --check social/worker.mjs`、`node --test social/tests/worker.test.mjs`。它沒有 npm 專案或前端建置流程。

修改後執行與變更相關的驗證；不要把 mock 測試通過描述成雲端部署、OAuth 或真實發文已驗證。涉及架構、排程、資料契約或驗證方式的變更時，同步修正專案記憶中的相關段落。
