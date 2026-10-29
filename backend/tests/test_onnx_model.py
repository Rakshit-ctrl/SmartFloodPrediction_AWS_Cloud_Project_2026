"""Plumbing tests with a SYNTHETIC ONNX graph that detects bright pixels (mean over channels > 0).

It proves preprocessing, inference, postprocessing, resizing, status and persistence work end to end.
It has nothing to do with floods, and no accuracy is implied.
"""
import hashlib
import json

import numpy as np
import pytest
from PIL import Image

from app.ml import registry
from tests.helpers import decode_png

onnx = pytest.importorskip("onnx")
pytest.importorskip("onnxruntime")
from onnx import TensorProto, helper  # noqa: E402

H = W = 32


def build_graph(kind: str, path):
    x = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 3, H, W])
    nodes = [helper.make_node("ReduceMean", ["input"], ["m"], axes=[1], keepdims=1)]
    if kind == "binary_logits":
        nodes[0].output[0] = "out"
        out_shape = [1, 1, H, W]
    elif kind == "binary_probabilities":
        nodes.append(helper.make_node("Sigmoid", ["m"], ["out"]))
        out_shape = [1, 1, H, W]
    else:  # multiclass_logits: channel 0 = -mean, channel 1 = +mean
        nodes += [helper.make_node("Neg", ["m"], ["n"]), helper.make_node("Concat", ["n", "m"], ["out"], axis=1)]
        out_shape = [1, 2, H, W]
    y = helper.make_tensor_value_info("out", TensorProto.FLOAT, out_shape)
    model = helper.make_model(helper.make_graph(nodes, "synthetic", [x], [y]), opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 8
    onnx.checker.check_model(model)
    onnx.save(model, str(path))


def install_model(tmp_path, monkeypatch, kind, width=W, height=H):
    build_graph(kind, tmp_path / "synthetic.onnx")
    out = {"type": kind}
    if kind == "multiclass_logits":
        out["flood_class_index"] = 1
    (tmp_path / "model.json").write_text(json.dumps({
        "name": "synthetic-brightness", "version": "test", "architecture": "synthetic", "format": "onnx",
        "weights_file": "synthetic.onnx",
        "input": {"width": width, "height": height, "channels": 3, "mean": [0.5] * 3, "std": [0.5] * 3, "scale": 255},
        "output": out,
    }))
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    registry.reset()


def half_black_half_white() -> bytes:
    import io
    arr = np.zeros((64, 64, 3), dtype=np.uint8)
    arr[:, 32:] = 255
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.parametrize("kind", ["binary_logits", "binary_probabilities", "multiclass_logits"])
def test_end_to_end_all_output_types(client, tmp_path, monkeypatch, kind):
    install_model(tmp_path, monkeypatch, kind)
    r = client.post("/api/satellite/analyze", files={"file": ("a.png", half_black_half_white(), "image/png")})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "completed" and d["model"]["state"] == "ready"
    mask = np.asarray(decode_png(d["mask"]["png_base64"]))
    assert mask.shape == (64, 64)  # resized back to the original image size
    assert (mask[:, 36:] == 255).all() and (mask[:, :28] == 0).all()  # bright side flagged, dark side not
    assert d["mask"]["flooded_pixels"] == 64 * 32


def test_model_status_and_version_identification(client, tmp_path, monkeypatch):
    install_model(tmp_path, monkeypatch, "binary_logits")
    d = client.get("/api/model").json()
    assert d["state"] == "ready" and d["name"] == "synthetic-brightness" and d["version"] == "test"
    assert d["weights_sha256"] == hashlib.sha256((tmp_path / "synthetic.onnx").read_bytes()).hexdigest()
    assert d["input"]["width"] == 32 and d["output"]["type"] == "binary_logits"
    assert client.get("/api/health").json()["model_configured"] is True


def test_declared_input_size_must_match_onnx(client, tmp_path, monkeypatch):
    install_model(tmp_path, monkeypatch, "binary_logits", width=64, height=64)  # ONNX graph is 32x32
    s = client.get("/api/model").json()
    assert s["state"] == "load_failed" and "model.json input" in s["message"] and "32" in s["message"]


def test_result_is_persisted_with_version_hash(client, tmp_path, monkeypatch):
    install_model(tmp_path, monkeypatch, "binary_logits")
    client.post("/api/satellite/analyze", files={"file": ("a.png", half_black_half_white(), "image/png")})
    row = client.get("/api/satellite/analyses").json()[0]
    assert row["model_name"] == "synthetic-brightness" and len(row["weights_sha256"]) == 64


def test_demo_tool_writes_a_loadable_synthetic_model(client, tmp_path, monkeypatch):
    from tools.make_synthetic_model import NAME, write_synthetic_model

    write_synthetic_model(tmp_path)
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    registry.reset()
    d = client.get("/api/model").json()
    assert d["state"] == "ready" and d["name"] == NAME and "NOT-A-FLOOD" in d["name"]
