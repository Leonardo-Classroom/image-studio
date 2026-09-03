// 專輯瀏覽器 Alpine 元件：版本切換、觸控手勢（左右換圖/上滑面板/下滑最愛）、面板狀態
document.addEventListener("alpine:init", () => {
  Alpine.data("viewer", (cfg) => ({
    versions: cfg.versions, // [{id, url, seed, created, prompt, favorited}]
    vi: Math.max(0, cfg.versions.length - 1),
    panel: localStorage.getItem("imgstudio.panel") === "1",
    collapsed: localStorage.getItem("imgstudio.collapsed") === "1",
    heart: false,
    _t: null,

    get cur() {
      return this.versions[this.vi] || null;
    },
    prevVersion() { if (this.vi > 0) this.vi--; },
    nextVersion() { if (this.vi < this.versions.length - 1) this.vi++; },
    openPanel(v) {
      this.panel = v;
      localStorage.setItem("imgstudio.panel", v ? "1" : "0");
    },
    toggleCollapsed() {
      this.collapsed = !this.collapsed;
      localStorage.setItem("imgstudio.collapsed", this.collapsed ? "1" : "0");
    },

    delVersion() {
      if (!this.cur || !confirm("刪除此版本？（進回收桶）")) return;
      fetch("/versions/" + this.cur.id + "/delete/", {
        method: "POST",
        headers: { "X-CSRFToken": cfg.csrf },
      }).then(() =>
        htmx.ajax("GET", cfg.itemUrl, { target: "#viewer-item", swap: "outerHTML" })
      );
    },

    favToggle() {
      if (!this.cur) return;
      fetch(cfg.favUrl.replace("/0/", "/" + this.cur.id + "/"), {
        method: "POST",
        headers: { "X-CSRFToken": cfg.csrf },
      })
        .then((r) => r.json())
        .then((d) => {
          this.cur.favorited = d.favorited;
          if (d.favorited) {
            this.heart = true;
            setTimeout(() => (this.heart = false), 900);
          }
        });
    },

    touchStart(e) {
      const t = e.changedTouches[0];
      this._t = { x: t.clientX, y: t.clientY, at: Date.now() };
    },
    touchEnd(e, zone) {
      if (!this._t) return;
      const t = e.changedTouches[0];
      const dx = t.clientX - this._t.x;
      const dy = t.clientY - this._t.y;
      const fast = Date.now() - this._t.at < 800;
      this._t = null;
      if (!fast) return;
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        if (zone === "main") {
          // 左右滑：換條目
          document.getElementById(dx < 0 ? "nav-next" : "nav-prev")?.click();
        } else {
          // 面板內左右滑：換版本
          dx < 0 ? this.nextVersion() : this.prevVersion();
        }
        return;
      }
      if (zone === "main" && Math.abs(dy) > 70 && Math.abs(dy) > Math.abs(dx) * 1.5) {
        if (dy < 0) this.openPanel(true); // 上滑：開面板
        else this.favToggle(); // 下滑：加入最愛
      }
      if (zone === "panel" && dy > 70 && Math.abs(dy) > Math.abs(dx) * 1.5) {
        this.openPanel(false); // 面板下滑：收合
      }
    },
  }));
});

// 鍵盤 ←→ 換條目（桌面）
document.addEventListener("keydown", (e) => {
  if (e.target.matches("input, textarea, select")) return;
  if (e.key === "ArrowLeft") document.getElementById("nav-prev")?.click();
  if (e.key === "ArrowRight") document.getElementById("nav-next")?.click();
});
