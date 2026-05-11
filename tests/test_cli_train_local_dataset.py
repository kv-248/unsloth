from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from unsloth_cli import app


def test_train_local_dataset_accepts_repeated_cli_values(tmp_path: Path) -> None:
    first = tmp_path / "train-a.jsonl"
    second = tmp_path / "train-b.jsonl"
    first.write_text('{"text":"a"}\n', encoding = "utf-8")
    second.write_text('{"text":"b"}\n', encoding = "utf-8")

    result = CliRunner().invoke(
        app,
        [
            "train",
            "--model",
            "unsloth/Qwen3-0.6B",
            "--local-dataset",
            str(first),
            "--local-dataset",
            str(second),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    resolved = yaml.safe_load(result.output)
    assert resolved["data"]["local_dataset"] == [str(first), str(second)]
