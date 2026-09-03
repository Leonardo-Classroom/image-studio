from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from prompts.models import SystemPrompt

# 取自 z-image_gen_from_prompt_set_zit.py 的 PROMPT_ADDITION_TEXT / NEGATIVE_PROMPT_TEXT
POSITIVE = (
    "一位女人名叫做HYX0920, masterpiece, best quality, high quality, ultra detailed, "
    "highly detailed, sharp focus, crisp details, professional, aesthetically pleasing, "
    "naked, huge breasts, 巨乳，大胸部"
)
NEGATIVE = (
    "(worst quality:1.4), (low quality:1.4), (normal quality:1.4), "
    "jpeg artifacts, signature, username, blurry, "
    "(deformed iris:1.3), (deformed pupils:1.3), "
    "(mutated hands:1.5), (poorly drawn hands:1.5), "
    "(extra fingers:1.5),(extra arms:1.5),grainy, noisy, "
    "oversaturated, underexposed, overexposed, "
    "(flat color:1.2), (dull colors:1.2), (muted colors:1.2), "
    "(soft focus:1.2), (diffused lighting:1.2),"
    "cartoon, 3d render, cgi, illustration, drawing, sketch, "
    "(vintage photo:1.2), (film grain:1.2), (bokeh background:1.3)"
)


class Command(BaseCommand):
    help = "為指定帳號匯入 zit 腳本的範例系統提示詞（正向前綴＋負向）"

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **opts):
        User = get_user_model()
        try:
            user = User.objects.get(username=opts["username"])
        except User.DoesNotExist:
            raise CommandError(f"找不到帳號：{opts['username']}")

        created = 0
        for name, kind, content in [
            ("HYX0920 角色前綴", SystemPrompt.Kind.POSITIVE, POSITIVE),
            ("ZIT 通用負向", SystemPrompt.Kind.NEGATIVE, NEGATIVE),
        ]:
            _, is_new = SystemPrompt.objects.get_or_create(
                owner=user, name=name, defaults={"kind": kind, "content": content}
            )
            created += is_new
        self.stdout.write(self.style.SUCCESS(f"完成，新增 {created} 筆（已存在的略過）"))
