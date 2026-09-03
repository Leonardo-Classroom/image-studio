import sys
import time

import pytest
from django.contrib.auth.models import User

from core import procs


@pytest.fixture
def client_logged(client, db):
    user = User.objects.create_user("tester", password="pw")
    client.force_login(user)
    return client


@pytest.fixture
def fake_service(tmp_path, settings, monkeypatch):
    """把服務定義換成一個長睡眠的假程序，run/ 導到 tmp。"""
    settings.RUN_DIR = tmp_path / "run"
    defs = {
        "comfyui": {
            "label": "ComfyUI", "desc": "假服務", "cwd": tmp_path,
            "cmd": [sys.executable, "-c", "import time; time.sleep(60)"],
            "port": 8188,
        },
        "aitoolkit": {
            "label": "ai-toolkit", "desc": "假服務", "cwd": tmp_path,
            "cmd": [sys.executable, "-c", "import time; time.sleep(60)"],
            "port": 7860,
        },
    }
    monkeypatch.setattr(procs, "service_defs", lambda: defs)
    monkeypatch.setattr(procs, "comfy_api_ok", lambda: False)
    yield defs
    for name in defs:
        procs.stop(name)


@pytest.mark.django_db
class TestProcs:
    def test_start_and_status(self, fake_service):
        assert procs.pid_of("comfyui") is None
        assert procs.start("comfyui") is True
        assert procs.pid_of("comfyui") is not None
        assert procs.start("comfyui") is False  # 已在跑不重複啟動

    def test_stop(self, fake_service):
        procs.start("comfyui")
        assert procs.stop("comfyui") is True
        assert procs.pid_of("comfyui") is None
        assert procs.stop("comfyui") is False

    def test_stale_pid_file_cleaned(self, fake_service, settings):
        run = settings.RUN_DIR
        run.mkdir(parents=True, exist_ok=True)
        (run / "comfyui.pid").write_text("999999999")
        assert procs.pid_of("comfyui") is None
        assert not (run / "comfyui.pid").exists()

    def test_log_written(self, fake_service):
        procs.start("aitoolkit")
        time.sleep(0.2)
        assert "面板啟動" in procs.log_tail("aitoolkit")
        procs.stop("aitoolkit")

    def test_missing_cwd_raises(self, fake_service, tmp_path):
        fake_service["comfyui"]["cwd"] = tmp_path / "nope"
        with pytest.raises(FileNotFoundError):
            procs.start("comfyui")


@pytest.mark.django_db
class TestServicesViews:
    def test_login_required(self, client):
        assert client.get("/services/").status_code == 302

    def test_page_renders(self, client_logged, fake_service):
        resp = client_logged.get("/services/")
        assert resp.status_code == 200
        assert "ComfyUI".encode() in resp.content
        assert "ai-toolkit".encode() in resp.content

    def test_start_stop_via_views(self, client_logged, fake_service):
        resp = client_logged.post("/services/comfyui/start/")
        assert resp.status_code == 200
        assert procs.pid_of("comfyui") is not None
        assert "運行中".encode() in resp.content
        resp = client_logged.post("/services/comfyui/stop/")
        assert procs.pid_of("comfyui") is None
        assert "已停止".encode() in resp.content

    def test_unknown_service_ignored(self, client_logged, fake_service):
        assert client_logged.post("/services/hack/start/").status_code == 200

    def test_settings_save_aitoolkit_fields(self, client_logged):
        from core.models import AppSetting

        client_logged.post("/settings/app/", {
            "comfyui_url": "", "threshold": "",
            "aitoolkit_cmd": "python run.py ui", "aitoolkit_port": "8675",
        })
        app = AppSetting.get()
        assert app.aitoolkit_cmd == "python run.py ui"
        assert app.aitoolkit_port == 8675
