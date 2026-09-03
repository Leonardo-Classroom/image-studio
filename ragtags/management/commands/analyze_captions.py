from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from sources.scan import iter_album_images
from ragtags.clustering import DEFAULT_THRESHOLD, cluster_fragments
from ragtags.embedder import get_embedder
from ragtags.slicing import slice_caption


class Command(BaseCommand):
    help = "對一個原專輯目錄跑 切片→bge-m3→分群，印出 tag 彙整結果（調閾值用）"

    def add_arguments(self, parser):
        parser.add_argument("album_dir")
        parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
        parser.add_argument("--top", type=int, default=100, help="最多顯示幾個 tag")

    def handle(self, *args, **opts):
        album = Path(opts["album_dir"])
        if not album.is_dir():
            raise CommandError(f"不是資料夾：{album}")

        entries = iter_album_images(album)
        fragments = [f.text for e in entries for f in slice_caption(e.caption)]
        self.stdout.write(f"圖片 {len(entries)} 張、片段 {len(fragments)} 個，嵌入中…")

        clusters, _ = cluster_fragments(
            fragments, get_embedder(), threshold=opts["threshold"]
        )
        clusters.sort(key=lambda c: -c.count)
        self.stdout.write(
            f"閾值 {opts['threshold']} → {len(clusters)} 個 tag：\n"
        )
        for c in clusters[: opts["top"]]:
            extra = ""
            if len(c.members) > 1:
                extra = "  ⇐ " + " / ".join(c.members[1:4]) + ("…" if len(c.members) > 4 else "")
            self.stdout.write(f"  [{c.count:4d}] {c.representative}{extra}")
