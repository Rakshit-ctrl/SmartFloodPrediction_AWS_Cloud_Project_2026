
"""
Baseline U-Net training for ClimateRiskFloodPrediction Track 1.

Inputs: TIFF bands 1 and 2 only.
Labels: binary PNG masks.
Device: CPU baseline (works with Intel Iris Xe systems).
Validation: deterministic tile-level holdout, not event-separated.

Assumption: values >= 30000 are invalid sentinels, based on the
observed 32765 values. Verify this if authoritative metadata becomes available.

The source dataset is read-only and is never modified.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, random_split


class FloodTileDataset(Dataset):
    def __init__(self, image_dir: Path, label_dir: Path):
        images = sorted(image_dir.glob("*.tif"))

        if not images:
            raise FileNotFoundError(f"No TIFF images found: {image_dir}")

        self.pairs = []
        missing = []

        for image_path in images:
            label_path = label_dir / f"{image_path.stem}.png"

            if label_path.exists():
                self.pairs.append((image_path, label_path))
            else:
                missing.append(image_path.name)

        if missing:
            raise FileNotFoundError(
                f"{len(missing)} images lack labels. "
                f"Examples: {missing[:5]}"
            )

    def __len__(self):
        return len(self.pairs)

    @staticmethod
    def normalize_band(band):
        band = band.astype(np.float32, copy=False)

        valid = np.isfinite(band) & (band < 30000)

        if not valid.any():
            return np.zeros_like(band, dtype=np.float32)

        values = band[valid]
        low, high = np.percentile(values, [2, 98])

        if not np.isfinite(low) or not np.isfinite(high) or high <= low:
            low = float(values.min())
            high = float(values.max())

        if high <= low:
            result = np.zeros_like(band, dtype=np.float32)
        else:
            safe = np.where(valid, band, low)
            result = (np.clip(safe, low, high) - low) / (high - low)

        result[~valid] = 0.0
        return result.astype(np.float32, copy=False)

    def __getitem__(self, index):
        image_path, label_path = self.pairs[index]

        with rasterio.open(image_path) as src:
            if src.count < 2:
                raise ValueError(
                    f"{image_path.name} contains only {src.count} band(s)"
                )

            band1 = src.read(1)
            band2 = src.read(2)

        image = np.stack(
            [
                self.normalize_band(band1),
                self.normalize_band(band2),
            ],
            axis=0,
        )

        with Image.open(label_path) as mask_image:
            mask = np.asarray(mask_image.convert("L"), dtype=np.uint8)

        values = np.unique(mask)

        if not np.all(np.isin(values, [0, 1, 255])):
            raise ValueError(
                f"Unexpected values in {label_path.name}: {values[:20]}"
            )

        # The inspected dataset uses 0 and 1.
        # 255 is accepted as foreground for compatibility.
        mask = (mask > 0).astype(np.float32)

        return (
            torch.from_numpy(image),
            torch.from_numpy(mask[None, ...]),
        )


class ConvBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()

        self.block = nn.Sequential(
            nn.Conv2d(
                in_channels, out_channels, kernel_size=3,
                padding=1, bias=False
            ),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(
                out_channels, out_channels, kernel_size=3,
                padding=1, bias=False
            ),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class UNet(nn.Module):
    def __init__(self, in_channels=2, base=8):
        super().__init__()

        self.enc1 = ConvBlock(in_channels, base)
        self.enc2 = ConvBlock(base, base * 2)
        self.enc3 = ConvBlock(base * 2, base * 4)
        self.bottleneck = ConvBlock(base * 4, base * 8)

        self.pool = nn.MaxPool2d(2)

        self.up3 = nn.ConvTranspose2d(
            base * 8, base * 4, kernel_size=2, stride=2
        )
        self.dec3 = ConvBlock(base * 8, base * 4)

        self.up2 = nn.ConvTranspose2d(
            base * 4, base * 2, kernel_size=2, stride=2
        )
        self.dec2 = ConvBlock(base * 4, base * 2)

        self.up1 = nn.ConvTranspose2d(
            base * 2, base, kernel_size=2, stride=2
        )
        self.dec1 = ConvBlock(base * 2, base)

        self.out = nn.Conv2d(base, 1, kernel_size=1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        bottleneck = self.bottleneck(self.pool(e3))

        d3 = self.dec3(torch.cat([self.up3(bottleneck), e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))

        return self.out(d1)


def dice_loss(logits, targets, eps=1e-6):
    probabilities = torch.sigmoid(logits)
    dims = (1, 2, 3)

    intersection = (probabilities * targets).sum(dims)
    denominator = probabilities.sum(dims) + targets.sum(dims)

    dice = (2 * intersection + eps) / (denominator + eps)
    return 1 - dice.mean()


def calculate_metrics(logits, targets, eps=1e-7):
    predictions = torch.sigmoid(logits) >= 0.5
    truth = targets >= 0.5
    dims = (1, 2, 3)

    tp = (predictions & truth).sum(dims).float()
    fp = (predictions & ~truth).sum(dims).float()
    fn = (~predictions & truth).sum(dims).float()

    dice = (2 * tp + eps) / (2 * tp + fp + fn + eps)
    iou = (tp + eps) / (tp + fp + fn + eps)
    precision = (tp + eps) / (tp + fp + eps)
    recall = (tp + eps) / (tp + fn + eps)

    return {
        "dice": dice.mean().item(),
        "iou": iou.mean().item(),
        "precision": precision.mean().item(),
        "recall": recall.mean().item(),
    }


def run_epoch(model, loader, optimizer, device, training):
    model.train(training)
    criterion = nn.BCEWithLogitsLoss()

    totals = {
        "loss": 0.0,
        "dice": 0.0,
        "iou": 0.0,
        "precision": 0.0,
        "recall": 0.0,
    }
    seen = 0

    context = torch.enable_grad() if training else torch.no_grad()

    with context:
        for images, masks in loader:
            images = images.to(device)
            masks = masks.to(device)

            if training:
                optimizer.zero_grad(set_to_none=True)

            logits = model(images)
            loss = criterion(logits, masks) + dice_loss(logits, masks)

            if training:
                loss.backward()
                optimizer.step()

            batch_size = images.size(0)
            totals["loss"] += loss.item() * batch_size

            for name, value in calculate_metrics(
                logits.detach(), masks
            ).items():
                totals[name] += value * batch_size

            seen += batch_size

    if seen == 0:
        raise RuntimeError("Data loader is empty.")

    return {name: value / seen for name, value in totals.items()}


def main():
    parser = argparse.ArgumentParser(
        description="Train a baseline U-Net on Track1 flood masks."
    )

    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(r"C:\Users\DELL\OneDrive\Desktop\Track1"),
    )
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument(
        "--patience",
        type=int,
        default=4,
        help="Number of epochs with no validation improvement before stopping.",
    )
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--val-fraction", type=float, default=0.15)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--base-channels", type=int, default=8)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backend") / "models" / "training_runs",
    )

    args = parser.parse_args()

    if args.epochs < 1 or args.batch_size < 1 or args.patience < 1:
        parser.error("--epochs, --batch-size, and --patience must be >= 1")

    if not 0.05 <= args.val_fraction <= 0.4:
        parser.error("--val-fraction must be between 0.05 and 0.4")

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(min(4, max(1, torch.get_num_threads())))

    dataset = FloodTileDataset(
        args.data_root / "train" / "images",
        args.data_root / "train" / "labels",
    )

    val_size = max(1, int(len(dataset) * args.val_fraction))
    train_size = len(dataset) - val_size

    generator = torch.Generator().manual_seed(args.seed)

    train_set, val_set = random_split(
        dataset,
        [train_size, val_size],
        generator=generator,
    )

    train_loader = DataLoader(
        train_set,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
    )
    val_loader = DataLoader(
        val_set,
        batch_size=1,
        shuffle=False,
        num_workers=0,
    )

    device = torch.device("cpu")
    model = UNet(in_channels=2, base=args.base_channels).to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "unet_sar2_best.pt"
    history_path = args.output_dir / "training_history.json"
    best_dice = -1.0
    best_epoch = 0
    epochs_without_improvement = 0
    history = []

    print(f"Labeled tiles: {len(dataset)}", flush=True)
    print(
        f"Training tiles: {train_size}; internal holdout: {val_size}",
        flush=True,
    )
    print("Input bands: 1 and 2 | Device: CPU", flush=True)
    print(f"Max epochs: {args.epochs} | Early stopping patience: {args.patience}", flush=True)
    print(
        "Note: tile-level holdout is not event/geography-separated.",
        flush=True,
    )

    for epoch in range(1, args.epochs + 1):
        train_metrics = run_epoch(
            model, train_loader, optimizer, device, training=True
        )
        val_metrics = run_epoch(
            model, val_loader, optimizer, device, training=False
        )

        epoch_record = {
            "epoch": epoch,
            "train_loss": train_metrics["loss"],
            "val_loss": val_metrics["loss"],
            "dice": val_metrics["dice"],
            "iou": val_metrics["iou"],
            "precision": val_metrics["precision"],
            "recall": val_metrics["recall"],
        }
        history.append(epoch_record)
        with history_path.open("w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        print(
            f"Epoch {epoch}/{args.epochs} | "
            f"train_loss={train_metrics['loss']:.4f} | "
            f"val_loss={val_metrics['loss']:.4f} | "
            f"Dice={val_metrics['dice']:.4f} | "
            f"IoU={val_metrics['iou']:.4f} | "
            f"Precision={val_metrics['precision']:.4f} | "
            f"Recall={val_metrics['recall']:.4f}",
            flush=True,
        )

        if val_metrics["dice"] > best_dice:
            best_dice = val_metrics["dice"]
            best_epoch = epoch
            epochs_without_improvement = 0

            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "architecture": "U-Net",
                    "input_channels": 2,
                    "input_bands": [1, 2],
                    "base_channels": args.base_channels,
                    "best_internal_holdout_dice": best_dice,
                    "best_epoch": best_epoch,
                    "total_epochs_trained": epoch,
                    "seed": args.seed,
                    "learning_rate": args.learning_rate,
                    "batch_size": args.batch_size,
                    "val_fraction": args.val_fraction,
                    "patience": args.patience,
                    "metrics": {
                        "val_dice": val_metrics["dice"],
                        "val_iou": val_metrics["iou"],
                        "val_precision": val_metrics["precision"],
                        "val_recall": val_metrics["recall"],
                        "val_loss": val_metrics["loss"],
                        "train_loss": train_metrics["loss"],
                    },
                    "normalization": (
                        "Per-tile 2nd/98th percentiles; "
                        "values >= 30000 treated as invalid"
                    ),
                },
                checkpoint_path,
            )

            print(
                f"Saved checkpoint (improved holdout Dice {best_dice:.4f} at epoch {best_epoch}): {checkpoint_path}",
                flush=True,
            )
        else:
            epochs_without_improvement += 1
            print(
                f"Holdout Dice did not improve ({val_metrics['dice']:.4f} <= {best_dice:.4f}). "
                f"Patience: {epochs_without_improvement}/{args.patience}",
                flush=True,
            )
            if epochs_without_improvement >= args.patience:
                print(
                    f"\nEarly stopping triggered at epoch {epoch}. "
                    f"No improvement for {args.patience} consecutive epochs. "
                    f"Best holdout Dice: {best_dice:.4f} at epoch {best_epoch}.",
                    flush=True,
                )
                break

    print("Training finished.", flush=True)
    print(f"Best holdout Dice: {best_dice:.4f} (at epoch {best_epoch})", flush=True)
    print(f"Checkpoint: {checkpoint_path}", flush=True)
    print(
        "This is a PyTorch checkpoint, not yet the ONNX model "
        "required by the existing API.",
        flush=True,
    )


if __name__ == "__main__":
    main()
