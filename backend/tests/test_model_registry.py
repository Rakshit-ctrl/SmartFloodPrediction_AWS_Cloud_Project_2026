import json
import sys

import pytest

from app.ml import registry


def valid_meta(**over):
    meta = {
        "name": "t", "version": "1", "architecture": "U-Net", "format": "onnx", "weights_file": "w.onnx",
        "input": {"width": 32, "height": 32, "channels": 3, "mean": [0, 0, 0], "std": [1, 1, 1]},
        "output": {"type": "binary_logits"},
    }
    meta.update(over)
    return meta


@pytest.fixture()
def model_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    registry.reset()
    return tmp_path


def write_meta(d, meta):
    (d / "model.json").write_text(json.dumps(meta))


def state():
    return registry.get_model()[1]


def test_default_is_not_configured(client):
    d = client.get("/api/model").json()
    assert d["state"] == "not_configured" and "MODEL_INTEGRATION" in d["message"]
    assert client.get("/api/health").json()["model_configured"] is False


def test_invalid_json_and_fields_are_reported_not_raised(model_dir):
    (model_dir / "model.json").write_text("{not json")
    assert state().state == "invalid_metadata"
    bad_cases = [
        valid_meta(input={"width": 32, "height": 32, "channels": 3, "mean": [0], "std": [1, 1, 1]}),  # mean length
        valid_meta(input={"width": 32, "height": 32, "channels": 3, "mean": [0, 0, 0], "std": [1, 0, 1]}),  # std 0
        valid_meta(output={"type": "multiclass_logits"}),  # class index missing
        valid_meta(output={"type": "binary_logits", "threshold": 1.5}),
        valid_meta(format="pytorch"),
        valid_meta(weights_file="../../etc/passwd"),
        valid_meta(weights_file="sub/dir.onnx"),
    ]
    for meta in bad_cases:
        write_meta(model_dir, meta)
        s = state()
        assert s.state == "invalid_metadata", meta
        assert "\n" not in s.message


def test_weights_missing(model_dir):
    write_meta(model_dir, valid_meta())
    s = state()
    assert s.state == "weights_missing" and s.name == "t" and s.version == "1"


def test_runtime_missing(model_dir, monkeypatch):
    write_meta(model_dir, valid_meta())
    (model_dir / "w.onnx").write_bytes(b"x")
    monkeypatch.setitem(sys.modules, "onnxruntime", None)  # makes `import onnxruntime` raise ImportError
    s = state()
    assert s.state == "runtime_missing" and "requirements-ml.txt" in s.message


def test_corrupt_weights_report_load_failed(model_dir):
    pytest.importorskip("onnxruntime")
    write_meta(model_dir, valid_meta())
    (model_dir / "w.onnx").write_bytes(b"this is not an onnx model")
    s = state()
    assert s.state == "load_failed" and s.name == "t"


def test_state_is_rechecked_so_adding_files_takes_effect(model_dir):
    assert state().state == "not_configured"
    write_meta(model_dir, valid_meta())
    assert state().state == "weights_missing"
