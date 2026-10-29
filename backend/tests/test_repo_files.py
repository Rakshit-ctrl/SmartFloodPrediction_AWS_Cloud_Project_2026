"""Regression tests for the corrupted files found in the original upload (literal backslash-n)."""
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[2]


def test_no_literal_backslash_n_in_text_config_files():
    for rel in (".gitignore", "backend/.env.example", "backend/requirements.txt"):
        assert "\\n" not in (ROOT / rel).read_text(), rel


def test_requirements_parse_and_include_all_packages():
    lines = [l.strip() for l in (ROOT / "backend/requirements.txt").read_text().splitlines() if l.strip()]
    names = {Requirement(l).name.lower() for l in lines}
    assert {"fastapi", "uvicorn", "sqlalchemy", "pydantic", "python-multipart", "python-dotenv", "requests", "numpy", "pillow"} <= names


def test_gitignore_protects_env_and_database():
    entries = (ROOT / ".gitignore").read_text().splitlines()
    assert ".env" in entries and "*.db" in entries


def test_env_example_has_no_secret_values():
    values = dict(l.split("=", 1) for l in (ROOT / "backend/.env.example").read_text().splitlines() if "=" in l)
    assert values["OPENWEATHER_API_KEY"] == ""
    assert {"DATABASE_URL", "CORS_ORIGINS", "UPLOAD_MAX_MB"} <= set(values)


def test_no_model_or_weights_are_committed():
    """The repository must never ship (or pretend to ship) a trained model."""
    models = ROOT / "backend" / "models"
    assert not (models / "model.json").exists()
    assert not [p for p in models.iterdir() if p.suffix in {".onnx", ".pt", ".pth", ".h5", ".ckpt", ".safetensors"}]
