"""Bounded reads of exact working-tree bytes or blobs from one fixed HEAD.

This reader is intentionally story-scoped and has no process-global source
context. Git is read-only; committed mode never falls back to a working-tree
file. Evidence contains hashes and lengths only, never source text.
"""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath, PureWindowsPath

try:
    from scripts import story_config
except ImportError:  # direct CLI import
    import story_config

MAX_SOURCE_BYTES = 1024 * 1024
UNKNOWN_COMMIT = "UNKNOWN"
METADATA_BASIS = "WORKING_TREE_REGISTRIES"


def _raw_snapshot(path: Path) -> tuple[str, str | None, int | None]:
    """Hash a bounded regular working-tree file without retaining its contents."""
    try:
        if not path.exists():
            return "MISSING", None, None
        if not path.is_file():
            return "UNREADABLE", None, None
        with path.open("rb") as handle:
            raw = handle.read(MAX_SOURCE_BYTES + 1)
    except OSError:
        return "UNREADABLE", None, None
    if len(raw) > MAX_SOURCE_BYTES:
        return "UNREADABLE", None, len(raw)
    return "READABLE", hashlib.sha256(raw).hexdigest(), len(raw)


class SourceReader:
    """Read sources from one selected story in raw or committed mode.

    ``root`` is resolved once to an explicit story root and exposed as
    ``reader.root``. ``read`` and ``text`` accept only paths beneath that root.
    Git-backed readers pin HEAD at construction; ``evidence`` fails if HEAD or
    any observed raw source changes before evidence is collected.
    """

    def __init__(self, root: Path | str, mode: str = "working-tree") -> None:
        if mode not in ("working-tree", "committed"):
            raise ValueError("source mode must be 'working-tree' or 'committed'")
        self.mode = mode
        supplied_root = Path(root).absolute()
        try:
            from scripts import review_bundle
        except ImportError:  # direct CLI import
            import review_bundle
        try:
            review_bundle._reject_links(supplied_root)
            self.root = story_config.resolve_root(supplied_root)
            review_bundle._reject_links(self.root)
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError("source reader requires one safe, selected story root") from exc

        self._review_bundle = review_bundle
        self._repo: Path | None = None
        self.commit = UNKNOWN_COMMIT
        try:
            repo_text = review_bundle._git(
                self.root, "rev-parse", "--show-toplevel"
            ).decode("utf-8", errors="strict").strip()
            repo = Path(repo_text).resolve()
            if not self.root.is_relative_to(repo):
                raise ValueError("selected story is outside its local Git repository")
            self._repo = repo
            self.commit = review_bundle._commit(repo, "HEAD")
        except ValueError as exc:
            if mode == "working-tree":
                self._repo = None
                self.commit = UNKNOWN_COMMIT
            else:
                raise ValueError("committed source mode requires a local Git repository with a readable HEAD") from exc
        except (OSError, UnicodeError, TypeError) as exc:
            raise ValueError("cannot pin local Git source context") from exc

        if mode == "committed" and self._repo is None:
            raise ValueError("committed source mode requires a local Git repository")
        self.source_mode = self.mode
        self._records: dict[str, dict] = {}
        self._reads: list[str] = []

    @staticmethod
    def _normalize(relative: str) -> str:
        if (not isinstance(relative, str) or not relative.strip()
                or any(ord(char) < 32 for char in relative)
                or Path(relative).is_absolute() or PureWindowsPath(relative).drive
                or ":" in relative):
            raise ValueError("source path must be a safe story-relative path")
        normalized = relative.replace("\\", "/")
        parts = PurePosixPath(normalized).parts
        if (not parts or normalized.startswith("/")
                or any(part in ("", ".", "..") for part in parts)):
            raise ValueError("source path must be a safe story-relative path")
        return "/".join(parts)

    def _path(self, relative: str) -> tuple[str, Path]:
        normalized = self._normalize(relative)
        try:
            path = self._review_bundle._story_source(self.root, normalized)
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError("source path is outside the selected story or uses a link") from exc
        return normalized, path

    @staticmethod
    def _limit(max_bytes: int) -> int:
        if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_SOURCE_BYTES:
            raise ValueError("source byte limit must be between 1 byte and 1 MiB")
        return max_bytes

    def _raw_bytes(self, path: Path, limit: int) -> bytes:
        try:
            if not path.is_file():
                raise ValueError("source is missing or is not a regular file")
            with path.open("rb") as handle:
                value = handle.read(limit + 1)
        except (OSError, ValueError) as exc:
            raise ValueError("working-tree source is missing or unreadable") from exc
        if len(value) > limit:
            raise ValueError("working-tree source exceeds its byte limit")
        return value

    def _selected(self, relative: str, path: Path, limit: int) -> tuple[bytes, str | None]:
        if self.mode == "working-tree":
            value = self._raw_bytes(path, limit)
            return value, self._blob_id(value)

        assert self._repo is not None
        try:
            repository_path = path.relative_to(self._repo).as_posix()
        except ValueError as exc:
            raise ValueError("committed source is outside the selected repository") from exc
        if PurePosixPath(repository_path).is_absolute() or ".." in PurePosixPath(repository_path).parts:
            raise ValueError("committed source escapes the selected repository")
        try:
            value, object_id = self._review_bundle._base_blob(
                self._repo, self.commit, repository_path
            )
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError("cannot read the selected committed source blob") from exc
        if object_id is None:
            raise ValueError("selected source is absent from the pinned commit")
        if len(value) > limit:
            raise ValueError("committed source exceeds its byte limit")
        return value, object_id

    def _blob_id(self, value: bytes) -> str:
        # The repository object format follows its commit ID width. For raw
        # non-Git stories, retain Git's conventional SHA-1 blob identity.
        algorithm = "sha256" if len(self.commit) == 64 else "sha1"
        digest = hashlib.new(algorithm)
        digest.update(b"blob " + str(len(value)).encode("ascii") + b"\0" + value)
        return digest.hexdigest()

    def read(self, relative: str, max_bytes: int = MAX_SOURCE_BYTES) -> bytes:
        """Read exact selected bytes, enforcing source/path and size bounds."""
        limit = self._limit(max_bytes)
        normalized, path = self._path(relative)
        selected, object_id = self._selected(normalized, path, limit)
        raw_status, raw_sha, raw_length = _raw_snapshot(path)
        if self.mode == "working-tree" and raw_status != "READABLE":
            raise ValueError("working-tree source is missing, unreadable, or too large")
        selected_sha = hashlib.sha256(selected).hexdigest()
        if (self.mode == "working-tree"
                and (raw_sha != selected_sha or raw_length != len(selected))):
            raise ValueError("working-tree source changed while it was read")
        record = {
            "selected_sha256": selected_sha,
            "selected_byte_length": len(selected),
            "git_blob_id": object_id,
            "raw_sha256": raw_sha,
            "raw_byte_length": raw_length,
            "observed_raw_status": raw_status,
        }
        prior = self._records.get(normalized)
        if prior is not None:
            for key in ("selected_sha256", "selected_byte_length", "git_blob_id",
                        "raw_sha256", "raw_byte_length", "observed_raw_status"):
                if prior[key] != record[key]:
                    raise ValueError("source changed during repeated reads")
        else:
            self._records[normalized] = record
        self._reads.append(normalized)
        return selected

    def checkpoint(self) -> int:
        """Mark a read boundary, including subsequent reads of known sources."""
        return len(self._reads)

    def evidence_since(self, checkpoint: int) -> dict:
        """Describe context reads while still checking every observed source.

        Validation-only sources are not context inputs. They remain part of
        ``evidence()`` and are checked for races even in this scoped view.
        """
        if type(checkpoint) is not int or not 0 <= checkpoint <= len(self._reads):
            raise ValueError('invalid source evidence checkpoint')
        report = self.evidence()
        selected = set(self._reads[checkpoint:])
        report['sources'] = {path: value for path, value in report['sources'].items()
                             if path in selected}
        report['scope'] = 'CONTEXT_READS_NOT_VALIDATION_AUDIT'
        return report

    def text(self, relative: str, max_bytes: int = MAX_SOURCE_BYTES) -> str:
        """Read strict UTF-8 text without newline normalization."""
        value = self.read(relative, max_bytes=max_bytes)
        try:
            return self._review_bundle._text(value, "selected source")
        except UnicodeDecodeError as exc:
            raise ValueError("selected source is not valid UTF-8") from exc

    def identity(self, relative: str) -> dict:
        """Return selected hashes for a source already read in this session."""
        normalized = self._normalize(relative)
        record = self._records.get(normalized)
        if record is None:
            raise ValueError("source identity is available only after an exact read")
        return {
            "selected_sha256": record["selected_sha256"],
            "selected_byte_length": record["selected_byte_length"],
            "git_blob_id": record["git_blob_id"],
        }

    def evidence(self) -> dict:
        """Return safe hashes and exact raw-vs-selected identity for each read."""
        if self._repo is not None:
            try:
                if self._review_bundle._commit(self._repo, "HEAD") != self.commit:
                    raise ValueError("HEAD changed during source reading")
            except ValueError as exc:
                raise ValueError("pinned Git HEAD changed or is no longer readable") from exc
        sources = {}
        for relative, record in sorted(self._records.items()):
            _, path = self._path(relative)
            raw_status, raw_sha, raw_length = _raw_snapshot(path)
            if (raw_status != record["observed_raw_status"]
                    or raw_sha != record["raw_sha256"]
                    or raw_length != record["raw_byte_length"]):
                raise ValueError("working-tree source changed after it was read")
            if raw_status == "MISSING":
                comparison = "MISSING"
            elif raw_status != "READABLE":
                comparison = "UNREADABLE"
            elif raw_sha == record["selected_sha256"] and raw_length == record["selected_byte_length"]:
                comparison = "MATCH"
            else:
                comparison = "DIFFERENT"
            sources[relative] = {
                "selected_sha256": record["selected_sha256"],
                "selected_byte_length": record["selected_byte_length"],
                "git_blob_id": record["git_blob_id"],
                "raw_sha256": raw_sha,
                "raw_byte_length": raw_length,
                "raw_status": comparison,
            }
        return {
            "mode": self.mode,
            "commit": self.commit,
            "metadata_basis": METADATA_BASIS,
            "sources": sources,
        }
