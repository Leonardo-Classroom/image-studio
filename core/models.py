from django.db import models


class AppSetting(models.Model):
    """全站設定（單例）。"""

    comfyui_url = models.CharField(max_length=200, default="http://127.0.0.1:8188")
    threshold = models.FloatField(default=0.78)  # tag 分群閾值（新專輯用）
    aitoolkit_cmd = models.CharField(
        max_length=300, default="python flux_train_ui.py"
    )  # 服務面板啟動 ai-toolkit 用的指令（於 ai-toolkit/ 目錄執行）
    aitoolkit_port = models.PositiveIntegerField(default=7860)  # 其 UI 埠號（開啟連結用）

    @classmethod
    def get(cls) -> "AppSetting":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
