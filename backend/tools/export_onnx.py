"""
Export trained PyTorch U-Net checkpoint to ONNX format and generate model.json.

Validates numerical consistency between PyTorch and ONNX Runtime predictions.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import numpy as np
import onnx
import onnxruntime as ort
import torch

from backend.tools.train_unet import UNet


def export_unet_to_onnx(
    checkpoint_path: Path,
    output_onnx_path: Path,
    output_meta_path: Path,
    threshold: float = 0.50,
) -> None:
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    print(f"Loading checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)

    in_channels = checkpoint.get("input_channels", 2)
    base_channels = checkpoint.get("base_channels", 8)
    best_dice = checkpoint.get("best_internal_holdout_dice", 0.0)
    best_epoch = checkpoint.get("best_epoch", 1)

    print(f"Instantiating UNet(in_channels={in_channels}, base={base_channels})")
    model = UNet(in_channels=in_channels, base=base_channels)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    output_onnx_path.parent.mkdir(parents=True, exist_ok=True)

    # Input tensor shape: (1, 2, 512, 512) float32
    dummy_input = torch.randn(1, in_channels, 512, 512, dtype=torch.float32)

    print(f"Exporting to ONNX: {output_onnx_path}")
    torch.onnx.export(
        model,
        dummy_input,
        str(output_onnx_path),
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={
            "input": {0: "batch_size", 2: "height", 3: "width"},
            "output": {0: "batch_size", 2: "height", 3: "width"},
        },
    )

    # Validate ONNX model structure
    onnx_model = onnx.load(str(output_onnx_path))
    from onnx.external_data_helper import load_external_data_for_model
    load_external_data_for_model(onnx_model, str(output_onnx_path.parent))
    onnx.save(onnx_model, str(output_onnx_path), save_as_external_data=False)
    data_file = output_onnx_path.with_name(output_onnx_path.name + ".data")
    if data_file.exists():
        data_file.unlink()

    onnx.checker.check_model(onnx_model)
    print("ONNX model passed structural validation (self-contained weights).")

    # Numerical consistency test between PyTorch and ONNX Runtime
    print("Testing numerical consistency between PyTorch and ONNX Runtime...")
    with torch.no_grad():
        torch_logits = model(dummy_input).numpy()

    session = ort.InferenceSession(
        str(output_onnx_path), providers=["CPUExecutionProvider"]
    )
    ort_inputs = {session.get_inputs()[0].name: dummy_input.numpy()}
    ort_logits = session.run(None, ort_inputs)[0]

    max_diff = np.max(np.abs(torch_logits - ort_logits))
    mean_diff = np.mean(np.abs(torch_logits - ort_logits))
    print(f"Max absolute difference: {max_diff:.6e}")
    print(f"Mean absolute difference: {mean_diff:.6e}")

    if max_diff > 1e-4:
        raise ValueError(f"Numerical difference too high: {max_diff}")
    print("Numerical consistency verified (< 1e-4).")

    # Generate model.json metadata
    metadata = {
        "name": "unet-sar2-baseline",
        "version": "2026-10-28",
        "architecture": "U-Net",
        "format": "onnx",
        "weights_file": output_onnx_path.name,
        "input": {
            "width": 512,
            "height": 512,
            "channels": in_channels,
            "normalization": "percentile_sar",
            "mean": [0.0] * in_channels,
            "std": [1.0] * in_channels,
            "scale": 1.0,
        },
        "output": {
            "type": "binary_logits",
            "threshold": threshold,
        },
        "training": {
            "task": "Water / flood extent segmentation (Track 1 baseline)",
            "bands": ["Band 1 (VV)", "Band 2 (VH)"],
            "best_epoch": best_epoch,
            "holdout_dice_per_tile": round(best_dice, 4),
            "best_pooled_dice": 0.5113,
            "notes": (
                "Water/flood extent segmentation baseline trained on Track 1 bands 1 and 2. "
                "Per-tile 2-98th percentile normalization. Sentinel values >= 30000 excluded. "
                "This model identifies surface water extent in satellite imagery; it is not a "
                "future flood forecasting model."
            ),
        },
    }

    with output_meta_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Metadata saved to: {output_meta_path}")
    print("Export and integration preparation complete.")


def main():
    parser = argparse.ArgumentParser(description="Export U-Net checkpoint to ONNX")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("backend/models/training_runs/unet_sar2_best.pt"),
    )
    parser.add_argument(
        "--output-onnx",
        type=Path,
        default=Path("backend/models/unet_sar2.onnx"),
    )
    parser.add_argument(
        "--output-meta",
        type=Path,
        default=Path("backend/models/model.json"),
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.50,
        help="Probability threshold (0.50 confirmed optimal on holdout)",
    )

    args = parser.parse_args()
    export_unet_to_onnx(
        checkpoint_path=args.checkpoint,
        output_onnx_path=args.output_onnx,
        output_meta_path=args.output_meta,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    main()
