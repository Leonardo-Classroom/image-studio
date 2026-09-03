import copy
import json

import pytest

from generation import workflows


class TestValidate:
    def test_valid_workflow(self, sample_workflow):
        ok, reason = workflows.validate(sample_workflow)
        assert ok and reason == ""

    def test_missing_positive(self, sample_workflow):
        sample_workflow["1"]["_meta"]["title"] = "something"
        ok, reason = workflows.validate(sample_workflow)
        assert not ok and "positive" in reason

    def test_missing_sampler_seed(self, sample_workflow):
        del sample_workflow["4"]["inputs"]["seed"]
        ok, reason = workflows.validate(sample_workflow)
        assert not ok and "seed" in reason

    def test_not_a_workflow(self):
        assert workflows.validate({"foo": "bar"})[0] is False
        assert workflows.validate([])[0] is False

    def test_positive_title_case_insensitive(self, sample_workflow):
        sample_workflow["1"]["_meta"]["title"] = "Positive"
        assert workflows.validate(sample_workflow)[0] is True


class TestPrepare:
    def test_fills_positive_and_negative(self, sample_workflow):
        out, _ = workflows.prepare(sample_workflow, "a cat", negative="blurry")
        assert out["1"]["inputs"]["text"] == "a cat"
        assert out["2"]["inputs"]["text"] == "blurry"

    def test_negative_untouched_when_none(self, sample_workflow):
        out, _ = workflows.prepare(sample_workflow, "a cat")
        assert out["2"]["inputs"]["text"] == "bad"

    def test_random_seed_assigned(self, sample_workflow):
        out, seed = workflows.prepare(sample_workflow, "x")
        assert out["4"]["inputs"]["seed"] == seed
        assert 0 <= seed <= workflows.SEED_MAX

    def test_explicit_seed(self, sample_workflow):
        out, seed = workflows.prepare(sample_workflow, "x", seed=42)
        assert seed == 42 and out["4"]["inputs"]["seed"] == 42

    def test_same_seed_for_all_samplers(self, sample_workflow):
        sample_workflow["6"] = {
            "class_type": "KSamplerAdvanced", "inputs": {"noise_seed": 1}
        }
        out, seed = workflows.prepare(sample_workflow, "x")
        assert out["4"]["inputs"]["seed"] == seed
        assert out["6"]["inputs"]["noise_seed"] == seed

    def test_size_fill(self, sample_workflow):
        out, _ = workflows.prepare(sample_workflow, "x", width=768, height=1024)
        assert out["3"]["inputs"]["width"] == 768
        assert out["3"]["inputs"]["height"] == 1024

    def test_input_not_mutated(self, sample_workflow):
        before = copy.deepcopy(sample_workflow)
        workflows.prepare(sample_workflow, "changed", negative="n", seed=7)
        assert sample_workflow == before

    def test_invalid_raises(self, sample_workflow):
        del sample_workflow["1"]
        with pytest.raises(ValueError):
            workflows.prepare(sample_workflow, "x")


class TestListWorkflows:
    def test_lists_valid(self, workflows_dir):
        infos = workflows.list_workflows()
        assert [(w.name, w.valid, w.has_negative) for w in infos] == [("basic", True, True)]

    def test_invalid_json_marked(self, workflows_dir):
        (workflows_dir / "broken.json").write_text("{not json", encoding="utf-8")
        infos = {w.name: w for w in workflows.list_workflows()}
        assert infos["broken"].valid is False

    def test_missing_positive_marked(self, workflows_dir, sample_workflow):
        sample_workflow["1"]["_meta"]["title"] = "other"
        (workflows_dir / "nopos.json").write_text(json.dumps(sample_workflow), encoding="utf-8")
        infos = {w.name: w for w in workflows.list_workflows()}
        assert infos["nopos"].valid is False and "positive" in infos["nopos"].reason

    def test_empty_dir_ok(self, tmp_path, settings):
        settings.WORKFLOWS_DIR = tmp_path / "nope"
        assert workflows.list_workflows() == []
