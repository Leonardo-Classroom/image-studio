from django.db import models


class DatasetRoot(models.Model):
    """資料集根路徑（本機、唯讀）。全站共用，設定頁管理。"""

    name = models.CharField(max_length=100)
    path = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.path})"
