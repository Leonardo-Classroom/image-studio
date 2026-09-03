# 圖像工作室（image-studio）

圖像訓練生成瀏覽系統：以 Django 打造的本機圖像生成與專輯瀏覽介面。
生成透過 ComfyUI API；資料集 caption 以本地 bge-m3 向量做 tag 分群與開關（RAG）。
規格見上層目錄 `SPEC.md`，任務與測試策略見 `TASKS.md` / `TEST_PLAN.md`。

## 功能總覽

- **會員**：Django auth，不開放註冊，帳號由 `/admin/` 建立；所有資料 per-user 隔離。
- **文字生成**：選工作流＋輸入 prompt → 佇列生成；歷史紀錄保留多版本、可重生。
- **專輯**：從資料集（圖片＋同名 `.txt` caption）挑原專輯建立：
  - 多層子資料夾自動**壓平**成一層（`sub1_sub2_檔名`，衝突加 `~n`）
  - caption 標點切片 → bge-m3 嵌入 → 相似片段跨圖分群成 **tag 開關牆**（附次數，預設全開）
  - 全域前綴 prompt；關掉的 tag（含語意相近句子片段）生成時從 caption 移除
  - **原資料集永遠唯讀**，所有調整只作用於專輯複本
  - 一鍵全部生成＋單張重生成，版本全保留
- **瀏覽器**：手機左右滑換圖、上滑開控制面板、下滑加最愛；桌面右欄常駐面板（可摺疊）＋ ←→ 鍵。
  面板內：版本切換（seed/時間/prompt 同步）、caption 手動編輯（向量重比對回 tag）、tag 即時開關、生成、刪版本。
- **總覽**：資料夾樹、拖曳移動、右鍵（桌面）/長按（手機）選單、專輯以第一張圖為封面。
- **最愛頁**、**回收桶**（軟刪除：還原/永久刪除）、**設定頁**（資料集根路徑、ComfyUI 位址、分群閾值、ai-toolkit 指令/埠號）。
- **服務控制面板**（`/services/`）：網頁上啟動/關閉 ComfyUI 與 ai-toolkit，即時狀態燈、log 尾端、開啟連結；
  與 `start.sh`/`stop.sh` 共用 `../run/*.pid`，兩邊狀態一致。

## 環境與啟動

conda 環境 `leo3.10`；同層目錄需有 `comfyui/`（引擎）與 `ai-toolkit/`（訓練，選用）。
一鍵建置：上層目錄 `./setup.sh`。

**一鍵啟停（建議）**——上層目錄：

```bash
./start.sh   # 啟動 ComfyUI + 網站(:8000) + 生成 worker；pid/log 在 run/
./stop.sh    # 停止全部（含面板啟動的 ai-toolkit）
# 無 GPU 環境測試：COMFYUI_ARGS=--cpu ./start.sh
```

ai-toolkit 由網頁「服務」面板啟停（預設跑 `python flux_train_ui.py`，可在設定頁改指令）。

手動逐一啟動（除錯用）：

```bash
conda activate leo3.10
python ../comfyui/main.py --listen 127.0.0.1 --port 8188   # 模型放 comfyui/models/checkpoints/
python manage.py runserver 0.0.0.0:8000
python manage.py run_worker   # 必須跑著才會生圖
```

首次使用：

```bash
python manage.py migrate
python manage.py createsuperuser   # 之後在 /admin/ 建其他帳號
./bin/tailwindcss -i static/css/input.css -o static/css/app.css --minify
```

## ComfyUI 工作流約定

在 ComfyUI 以「匯出 (API)」存 JSON 放進 `workflows/`。節點 **title** 約定：

- `positive`（必要）：正向 prompt 文字節點；缺少會在選單標示不可用
- `negative`（選用）：負向 prompt

`EmptyLatentImage` 尺寸與 `KSampler(.Advanced)` seed 由系統自動填；每次生成 seed 隨機。

## RAG tag 管線

閾值預設 0.78（bge-m3 實測：同義片段 0.80–0.93、無關 0.48–0.63），設定頁可調。
建專輯前想先看分群品質：

```bash
python manage.py analyze_captions /path/to/原專輯 --threshold 0.78
```

## 測試

```bash
python -m pytest            # small tests（fake embedder/comfy，秒級）
python -m pytest -m slow -o addopts=""    # 真 bge-m3 smoke
```
