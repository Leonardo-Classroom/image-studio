from django.conf import settings
from django.db import models


class SystemPrompt(models.Model):
    """可重用的系統提示詞：建立專輯時選來套用（正向前綴或負向）。"""

    class Kind(models.TextChoices):
        POSITIVE = "positive", "正向前綴"
        NEGATIVE = "negative", "負向"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.POSITIVE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["kind", "name"]

    def __str__(self):
        return f"[{self.get_kind_display()}] {self.name}"
