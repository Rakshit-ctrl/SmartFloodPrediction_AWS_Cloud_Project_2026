"""Model contract and metadata schema.

A model is installed by placing `model.json` and the weights file it names in MODEL_DIR
(default backend/models). Nothing is bundled with this repository.
"""
from abc import ABC, abstractmethod
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator


class ModelOutputError(Exception):
    """The model produced output that does not match what model.json declares."""


class InputSpec(BaseModel):
    width: int = Field(gt=0, le=4096)
    height: int = Field(gt=0, le=4096)
    channels: Literal[1, 2, 3]
    mean: list[float]
    std: list[float]
    scale: float = Field(default=255.0, gt=0)  # pixel values are divided by this before mean/std
    normalization: str = "mean_std"  # "mean_std" or "percentile_sar"

    @model_validator(mode="after")
    def _check_lengths(self):
        if len(self.mean) != self.channels or len(self.std) != self.channels:
            raise ValueError("mean and std must each have one value per channel")
        if any(s <= 0 for s in self.std):
            raise ValueError("std values must be positive")
        return self


class OutputSpec(BaseModel):
    type: Literal["binary_logits", "binary_probabilities", "multiclass_logits"]
    flood_class_index: int | None = Field(default=None, ge=0)
    threshold: float = Field(default=0.5, gt=0, lt=1)

    @model_validator(mode="after")
    def _check_class(self):
        if self.type == "multiclass_logits" and self.flood_class_index is None:
            raise ValueError("flood_class_index is required for multiclass_logits")
        return self


class ModelMeta(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=80)
    architecture: str = Field(min_length=1, max_length=80)  # free label, e.g. "U-Net"
    format: Literal["onnx"]
    weights_file: str = Field(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.\-]*$")  # file name only, no paths
    input: InputSpec
    output: OutputSpec
    training: dict | None = None  # free-form notes supplied by whoever trained it; not verified here

    @field_validator("weights_file")
    @classmethod
    def _no_traversal(cls, v: str):
        if ".." in v:
            raise ValueError("weights_file must be a plain file name")
        return v


class SegmentationModel(ABC):
    meta: ModelMeta

    @abstractmethod
    def predict(self, image: np.ndarray) -> np.ndarray:
        """image: uint8 array (H, W, C) with C == meta.input.channels.
        Returns a boolean array (H, W), same size as the input, True where the model predicts flood."""
