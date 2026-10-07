"""Repository and file governance checks for context collection."""

from __future__ import annotations

import fnmatch
from pathlib import PurePosixPath


BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".jar", ".exe", ".dll", ".class"}
GENERATED_PATTERNS = ("*.min.js", "*.generated.*", "*_generated.*", "vendor/*", "dist/*", "build/*")
SENSITIVE_PATTERNS = (".env*", "**/secrets.*", "**/*credential*", "**/*private*", "**/*token*")


def should_skip_file(file_path: str, content: bytes | str | None = None) -> tuple[bool, str]:
    normalized = file_path.replace("\\", "/")
    suffix = PurePosixPath(normalized).suffix.lower()
    if suffix in BINARY_EXTENSIONS:
        return True, "binary file"
    if any(fnmatch.fnmatch(normalized, pattern) for pattern in GENERATED_PATTERNS):
        return True, "generated or vendored file"
    if any(fnmatch.fnmatch(normalized, pattern) for pattern in SENSITIVE_PATTERNS):
        return True, "sensitive path"
    if isinstance(content, bytes) and b"\x00" in content[:4096]:
        return True, "binary content"
    return False, ""


class SensitivePathFilter:
    def allow(self, file_path: str) -> bool:
        return not should_skip_file(file_path)[0]


class RepositoryAccessControl:
    def __init__(self, enabled_repositories: set[str] | None = None):
        self.enabled_repositories = enabled_repositories or set()

    def can_review(self, repository: str) -> bool:
        return not self.enabled_repositories or repository in self.enabled_repositories

    def is_path_allowed(self, file_path: str) -> bool:
        return not should_skip_file(file_path)[0]
