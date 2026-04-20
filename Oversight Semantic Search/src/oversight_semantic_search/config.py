from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _default_workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_oig_project_root() -> Path:
    return _default_workspace_root().parent / "OIG Scrape"


@dataclass(slots=True)
class SearchConfig:
    workspace_root: Path = _default_workspace_root()
    oig_project_root: Path = _default_oig_project_root()
    oig_db_path: Path = _default_oig_project_root() / "data" / "oig_reports.sqlite3"
    index_dir: Path = _default_workspace_root() / "data" / "index"
    chunk_char_limit: int = 12000
    max_features: int = 8000
    latent_dimensions: int = 192
    min_token_length: int = 2
    stopword_path: Path | None = None

    @classmethod
    def from_env(cls) -> "SearchConfig":
        default = cls()
        return cls(
            workspace_root=Path(os.getenv("OSS_WORKSPACE_ROOT", str(default.workspace_root))),
            oig_project_root=Path(os.getenv("OSS_OIG_PROJECT_ROOT", str(default.oig_project_root))),
            oig_db_path=Path(os.getenv("OSS_OIG_DB_PATH", str(default.oig_db_path))),
            index_dir=Path(os.getenv("OSS_INDEX_DIR", str(default.index_dir))),
            chunk_char_limit=int(os.getenv("OSS_CHUNK_CHAR_LIMIT", str(default.chunk_char_limit))),
            max_features=int(os.getenv("OSS_MAX_FEATURES", str(default.max_features))),
            latent_dimensions=int(os.getenv("OSS_LATENT_DIMENSIONS", str(default.latent_dimensions))),
            min_token_length=int(os.getenv("OSS_MIN_TOKEN_LENGTH", str(default.min_token_length))),
            stopword_path=Path(os.environ["OSS_STOPWORD_PATH"]) if os.getenv("OSS_STOPWORD_PATH") else None,
        )
