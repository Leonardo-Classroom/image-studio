import time

from django.core.management.base import BaseCommand

from generation.worker import process_one


class Command(BaseCommand):
    help = "生成佇列 worker：逐一送 ComfyUI（單 GPU 序列）"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="只處理一件就結束")

    def handle(self, *args, **options):
        self.stdout.write("worker 啟動，等待佇列…")
        while True:
            worked = process_one()
            if options["once"]:
                break
            if not worked:
                time.sleep(1)
