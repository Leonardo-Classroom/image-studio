# 圖像工作室（image-studio）

圖像訓練生成瀏覽系統：以 Django 打造的本機圖像生成與專輯瀏覽介面，生成透過 ComfyUI API，
caption tag 以本地 bge-m3 向量分群管理（RAG）。規格見上層目錄 `SPEC.md`。

## 環境

- conda 環境 `leo3.10`（Python 3.10）
- 同層目錄需有 `comfyui/`（生成引擎）與 `ai-toolkit/`（訓練工具，選用）
- 一鍵建置：上層目錄 `./setup.sh`

## 啟動

```bash
conda activate leo3.10
# 1. 啟動 ComfyUI（另一個終端）
python ../comfyui/main.py --listen 127.0.0.1 --port 8188
# 2. 啟動網站
python manage.py runserver 0.0.0.0:8000
# 3. 生成佇列 worker（之後的 scope 加入）
```

首次使用：`python manage.py migrate && python manage.py createsuperuser`，
帳號一律由 `/admin/` 建立（不開放註冊）。

## Tailwind

樣式用 Tailwind standalone CLI（`bin/tailwindcss`，不進 git；`setup.sh` 會下載）：

```bash
./bin/tailwindcss -i static/css/input.css -o static/css/app.css --minify   # 開發時加 --watch
```

## ComfyUI 工作流約定

在 ComfyUI 以「匯出 (API)」存 JSON 放進 `workflows/`。節點 **title** 命名約定：

- `positive`（必要）：正向 prompt 的文字節點
- `negative`（選用）：負向 prompt

尺寸與 seed 由系統自動尋找 `EmptyLatentImage` / `KSampler` 填入。
