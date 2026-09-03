import numpy as np
from django.conf import settings
from django.db import models
from django.utils import timezone


class Folder(models.Model):
    """專輯總覽的資料夾（樹狀、per-user）。"""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def is_descendant_of(self, other) -> bool:
        node = self
        while node is not None:
            if node.pk == other.pk:
                return True
            node = node.parent
        return False


class Album(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        READY = "ready", "就緒"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    folder = models.ForeignKey(
        Folder, null=True, blank=True, on_delete=models.SET_NULL, related_name="albums"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    workflow_name = models.CharField(max_length=200, blank=True, default="")
    source_path = models.CharField(max_length=500)  # 原專輯絕對路徑（唯讀來源）
    prefix = models.TextField(blank=True, default="")  # 全域前綴 prompt
    threshold = models.FloatField(default=0.78)  # 建立時使用的分群閾值
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    @property
    def pending_jobs(self) -> int:
        from generation.models import GenerationJob

        return GenerationJob.objects.filter(
            album_item__album=self,
            status__in=[GenerationJob.Status.PENDING, GenerationJob.Status.RUNNING],
        ).count()

    @property
    def done_count(self) -> int:
        return self.items.filter(versions__isnull=False).distinct().count()


class AlbumItem(models.Model):
    """專輯內一張圖的條目：原圖 + caption 快照 + 目前生效 caption。"""

    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name="items")
    order = models.PositiveIntegerField()
    flat_name = models.CharField(max_length=300)  # 壓平後檔名
    source_image = models.CharField(max_length=500)  # 原圖絕對路徑
    original_caption = models.TextField(blank=True, default="")  # 建立時快照，不再變動
    caption = models.TextField(blank=True, default="")  # 目前生效（可手動編輯）

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["album", "flat_name"], name="uniq_album_flatname")
        ]


class Tag(models.Model):
    """專輯層級的 tag 群組（開關）。centroid 供手動編輯 caption 後重新比對。"""

    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name="tags")
    text = models.CharField(max_length=300)  # 代表文字（最高頻片段）
    enabled = models.BooleanField(default=True)
    count = models.PositiveIntegerField(default=0)
    centroid = models.BinaryField(null=True, blank=True)  # np.float32 bytes

    class Meta:
        ordering = ["-count", "id"]

    def __str__(self):
        return self.text

    def get_centroid(self) -> np.ndarray | None:
        if not self.centroid:
            return None
        return np.frombuffer(self.centroid, dtype=np.float32)

    def set_centroid(self, vec: np.ndarray):
        self.centroid = np.asarray(vec, dtype=np.float32).tobytes()


class TagOccurrence(models.Model):
    """某 tag 在某條目 caption 中的一個片段位置（span 對應 item.caption）。"""

    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="occurrences")
    item = models.ForeignKey(AlbumItem, on_delete=models.CASCADE, related_name="occurrences")
    start = models.PositiveIntegerField()
    end = models.PositiveIntegerField()
    text = models.CharField(max_length=500)

    class Meta:
        ordering = ["start"]
