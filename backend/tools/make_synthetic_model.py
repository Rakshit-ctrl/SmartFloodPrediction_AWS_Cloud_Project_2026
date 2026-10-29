"""Create a SYNTHETIC demo model so the whole upload -> inference -> overlay pipeline can be exercised.

THIS IS NOT A FLOOD MODEL. It marks pixels brighter than mid-grey (which includes clouds, snow,
bright roofs). It exists only to prove the plumbing works before real weights are available.
Requires: pip install -r requirements-dev-full.txt (needs the `onnx` package).

Usage (from backend/):
    python tools/make_synthetic_model.py --out models_demo
"""
import argparse
import json
from pathlib import Path

import onnx
from onnx import TensorProto, helper

NAME = "synthetic-brightness-DEMO-NOT-A-FLOOD-MODEL"


def write_synthetic_model(out_dir, size: int = 256) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    x = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 3, size, size])
    y = helper.make_tensor_value_info("out", TensorProto.FLOAT, [1, 1, size, size])
    node = helper.make_node("ReduceMean", ["input"], ["out"], axes=[1], keepdims=1)
    model = helper.make_model(helper.make_graph([node], "synthetic_brightness", [x], [y]),
                              opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 8
    onnx.checker.check_model(model)
    onnx.save(model, str(out_dir / "synthetic.onnx"))
    meta = {
        "name": NAME,
        "version": "demo",
        "architecture": "none (mean-brightness threshold)",
        "format": "onnx",
        "weights_file": "synthetic.onnx",
        "input": {"width": size, "height": size, "channels": 3, "mean": [0.5, 0.5, 0.5], "std": [0.5, 0.5, 0.5], "scale": 255},
        "output": {"type": "binary_logits", "threshold": 0.5},
        "training": {"notes": "Synthetic pipeline test. Not trained. Not a flood detector."},
    }
    (out_dir / "model.json").write_text(json.dumps(meta, indent=2))
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="models_demo", help="output directory (default: models_demo)")
    parser.add_argument("--size", type=int, default=256, help="model input width/height in pixels")
    args = parser.parse_args()
    path = write_synthetic_model(args.out, args.size)
    print(f"Wrote {path / 'model.json'} and {path / 'synthetic.onnx'}")
    print(f"Model name: {NAME}")


if __name__ == "__main__":
    main()
