// 專輯總覽：拖曳移動、長按選單、選單動作（htmx.ajax 重繪 #overview）
(function () {
  function currentFolder() {
    return document.getElementById("overview")?.dataset.folder || "";
  }

  function post(url, values) {
    values = Object.assign({ current_folder: currentFolder() }, values || {});
    htmx.ajax("POST", url, { target: "#overview", swap: "outerHTML", values });
  }

  window.ovRename = function (menu) {
    const name = prompt("新名稱：", menu.name);
    if (!name || !name.trim()) return;
    post(`/${menu.kind === "folder" ? "folders" : "albums"}/${menu.id}/rename/`, { name: name.trim() });
  };

  window.ovDelete = function (menu) {
    const what = menu.kind === "folder" ? "資料夾（內容物會移到上層）" : "專輯（進回收桶）";
    if (!confirm(`確定刪除${what}「${menu.name}」？`)) return;
    post(`/${menu.kind === "folder" ? "folders" : "albums"}/${menu.id}/delete/`);
  };

  window.ovMoveUp = function (menu) {
    // 移到上層 = 移到目前資料夾的父層；由後端依 target 空值處理為根層
    const grid = document.getElementById("overview");
    const parent = grid?.dataset.parentFolder || "";
    post(`/${menu.kind === "folder" ? "folders" : "albums"}/${menu.id}/move/`, { target: parent });
  };

  // --- 拖曳 ---
  document.addEventListener("dragstart", (e) => {
    const card = e.target.closest("[data-drag]");
    if (!card) return;
    e.dataTransfer.setData("text/plain", card.dataset.drag);
    e.dataTransfer.effectAllowed = "move";
  });
  document.addEventListener("dragover", (e) => {
    const zone = e.target.closest("[data-drop]");
    if (!zone) return;
    e.preventDefault();
    zone.classList.add("ring-2", "ring-violet-500");
  });
  document.addEventListener("dragleave", (e) => {
    const zone = e.target.closest("[data-drop]");
    zone?.classList.remove("ring-2", "ring-violet-500");
  });
  document.addEventListener("drop", (e) => {
    const zone = e.target.closest("[data-drop]");
    if (!zone) return;
    e.preventDefault();
    zone.classList.remove("ring-2", "ring-violet-500");
    const [kind, id] = (e.dataTransfer.getData("text/plain") || "").split(":");
    if (!kind || !id) return;
    const target = zone.dataset.drop; // 空字串 = 根層
    if (kind === "folder" && target === id) return;
    post(`/${kind === "folder" ? "folders" : "albums"}/${id}/move/`, { target });
  });

  // --- 手機長按開選單 ---
  let pressTimer = null;
  document.addEventListener("touchstart", (e) => {
    const card = e.target.closest("[data-drag]");
    if (!card) return;
    const t = e.touches[0];
    pressTimer = setTimeout(() => {
      window._ovMenuOpen = true;
      setTimeout(() => (window._ovMenuOpen = false), 400);
      const [kind, id] = card.dataset.drag.split(":");
      window.dispatchEvent(new CustomEvent("ov-menu", {
        detail: { kind, id: Number(id), name: card.dataset.name || "", x: t.clientX, y: t.clientY },
      }));
    }, 550);
  }, { passive: true });
  ["touchend", "touchmove", "touchcancel"].forEach((ev) =>
    document.addEventListener(ev, () => clearTimeout(pressTimer), { passive: true })
  );
})();
