import json

import pytest
from django.contrib.auth.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user("tester", password="pw")


@pytest.fixture
def other_user(db):
    return User.objects.create_user("other", password="pw")


@pytest.fixture
def client_logged(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def sample_workflow():
    """最小可用的 API-format 工作流：positive/negative/latent/sampler/save。"""
    return {
        "1": {"class_type": "CLIPTextEncode", "inputs": {"text": "placeholder"},
              "_meta": {"title": "positive"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "bad"},
              "_meta": {"title": "negative"}},
        "3": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512}},
        "4": {"class_type": "KSampler", "inputs": {"seed": 0, "steps": 20}},
        "5": {"class_type": "SaveImage", "inputs": {"images": ["4", 0]}},
    }


@pytest.fixture
def workflows_dir(tmp_path, settings, sample_workflow):
    d = tmp_path / "workflows"
    d.mkdir()
    (d / "basic.json").write_text(json.dumps(sample_workflow), encoding="utf-8")
    settings.WORKFLOWS_DIR = d
    return d


@pytest.fixture
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT
