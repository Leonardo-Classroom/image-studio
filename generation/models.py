from django.conf import settings
from django.db import models


class TextSession(models.Model):
    """純文字生成的一個條目；多個版本掛在底下。"""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    workflow_name = models.CharField(max_length=200)
    prompt = models.TextField()
    negative = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.prompt[:50]


class GeneratedImage(models.Model):
    """一次生成的結果（= 一個版本）。之後專輯條目的版本也用此模型。"""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text_session = models.ForeignKey(
        TextSession, null=True, blank=True, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="generated/%Y/%m/")
    final_prompt = models.TextField()
    negative = models.TextField(blank=True, default="")
    seed = models.BigIntegerField()
    workflow_name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]


class GenerationJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "排隊中"
        RUNNING = "running", "生成中"
        DONE = "done", "完成"
        FAILED = "failed", "失敗"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text_session = models.ForeignKey(
        TextSession, null=True, blank=True, on_delete=models.CASCADE, related_name="jobs"
    )
    workflow_name = models.CharField(max_length=200)
    positive = models.TextField()
    negative = models.TextField(blank=True, default="")
    seed = models.BigIntegerField(null=True, blank=True)  # None = 執行時隨機
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    prompt_id = models.CharField(max_length=64, blank=True, default="")
    error = models.TextField(blank=True, default="")
    result = models.ForeignKey(
        GeneratedImage, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def retry(self):
        self.status = self.Status.PENDING
        self.error = ""
        self.prompt_id = ""
        self.save(update_fields=["status", "error", "prompt_id"])
