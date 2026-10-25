"""Read registered local Git evidence without editing the evaluated repository."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import subprocess
from time import monotonic
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict

from promptpatch.tool_support import AuditedTools, ToolError, read_snapshot


@dataclass(frozen=True)
class RepositoryAccess:
    """Trusted caller configuration, never derived from source/model content."""

    root: Path
    prompt_paths: frozenset[str]


class GitPromptEvidence(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    project_id: str
    prompt_version_id: str
    commit_sha: str
    prompt_relpath: str
    content: str
    content_hash: str
    source_ref: str
    content_is_data: bool = True


class GitDiffEvidence(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    project_id: str
    base_version_id: str
    target_version_id: str
    base_sha: str
    target_sha: str
    prompt_relpath: str
    diff_text: str
    source_refs: list[str]
    content_is_data: bool = True


class GitEvidenceTool(AuditedTools):
    def __init__(self, db_path, project_access, *, max_prompt_bytes=65536,
                 max_diff_bytes=131072, timeout_seconds=5.0):
        super().__init__(db_path)
        self._access = MappingProxyType({
            project: RepositoryAccess(Path(access.root).resolve(), frozenset(access.prompt_paths))
            for project, access in project_access.items()
        })
        if max_prompt_bytes < 1 or max_diff_bytes < 1 or timeout_seconds <= 0:
            raise ValueError("Tool budgets must be positive.")
        self.max_prompt_bytes = max_prompt_bytes
        self.max_diff_bytes = max_diff_bytes
        self.timeout_seconds = timeout_seconds

    def _git(self, root, args, output_limit):
        # Only these read capabilities exist; no model-selected Git subcommand.
        if not args or args[0] not in {"rev-parse", "cat-file", "ls-tree", "diff"}:
            raise ToolError("unsupported_operation", "Git operation is not allowed.")
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_TERMINAL_PROMPT="0", GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1")
        command = ["git", "--no-optional-locks", "--literal-pathspecs",
                   "-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false",
                   "-c", "core.pager=cat", "-C", str(root), *args]
        deadline = monotonic() + self.timeout_seconds
        with subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
            try:
                output = bytearray()
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while True:
                        remaining = deadline - monotonic()
                        if remaining <= 0 or not selector.select(remaining):
                            raise ToolError("git_timeout", "Git evidence read timed out.")
                        chunk = os.read(process.stdout.fileno(), min(65536, output_limit + 1 - len(output)))
                        if not chunk:
                            break
                        output.extend(chunk)
                        if len(output) > output_limit:
                            raise ToolError("output_limit", "Git evidence exceeds the output budget.")
                if process.wait(timeout=max(0.001, deadline - monotonic())):
                    raise ToolError("git_failed", "Git evidence is unavailable.")
                return bytes(output)
            except subprocess.TimeoutExpired:
                raise ToolError("git_timeout", "Git evidence read timed out.") from None
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()

    @staticmethod
    def _validate_sha(sha):
        if not isinstance(sha, str) or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", sha) is None:
            raise ToolError("invalid_ref", "A full lowercase commit SHA is required.")

    def _location(self, project_id, relpath):
        access = self._access.get(project_id)
        if access is None:
            raise ToolError("repository_denied", "No repository is allowed for this project.")
        if (not isinstance(relpath, str) or not relpath or len(relpath) > 256
                or any(ord(char) < 32 for char in relpath) or "\\" in relpath or ":" in relpath
                or PurePosixPath(relpath).is_absolute()
                or any(part in {"", ".", "..", ".git"} for part in relpath.split("/"))):
            raise ToolError("invalid_path", "A safe relative prompt path is required.")
        if relpath not in access.prompt_paths:
            raise ToolError("path_denied", "Prompt path is not allowlisted.")
        root = access.root
        if (not root.is_dir() or root.resolve() != root or not (root / ".git").is_dir()
                or not (root / relpath).resolve().is_relative_to(root)):
            raise ToolError("repository_denied", "Repository or prompt location is not allowed.")
        for name in (".git", ".git/config", ".git/objects"):
            if not (root / name).resolve().is_relative_to(root):
                raise ToolError("repository_denied", "External Git metadata is not allowed.")
        if (root / ".git/objects/info/alternates").exists() or (root / ".git/commondir").exists():
            raise ToolError("repository_denied", "Shared external object stores are not supported.")
        if Path(self._git(root, ["rev-parse", "--show-toplevel"], 4096).decode().strip()).resolve() != root:
            raise ToolError("repository_denied", "Repository root differs from its allowlist entry.")
        return root

    def _snapshot(self, project_id, sha, relpath, root):
        self._validate_sha(sha)
        with read_snapshot(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM prompt_versions WHERE project_id=? AND git_commit_sha=? AND prompt_path=? "
                "ORDER BY created_at,id LIMIT 1", (project_id, sha, relpath),
            ).fetchone()
        if row is None:
            raise ToolError("source_not_registered", "Prompt snapshot is not registered in this project.")
        if self._git(root, ["cat-file", "-t", sha], 64).strip() != b"commit":
            raise ToolError("invalid_ref", "The registered SHA must identify a commit.")
        entry = self._git(root, ["ls-tree", "-z", sha, "--", relpath], 4096)
        if not entry:
            raise ToolError("missing_file", "Prompt is absent from the registered commit.")
        header, _, actual_path = entry.rstrip(b"\0").partition(b"\t")
        fields = header.split()
        if (len(fields) != 3 or fields[0] not in {b"100644", b"100755"}
                or fields[1] != b"blob" or actual_path.decode() != relpath):
            raise ToolError("invalid_file", "Prompt must be a regular tracked file.")
        blob = fields[2].decode()
        size = int(self._git(root, ["cat-file", "-s", blob], 64).strip())
        if size > self.max_prompt_bytes:
            raise ToolError("file_limit", "Prompt exceeds the file budget.")
        content = self._git(root, ["cat-file", "blob", blob], self.max_prompt_bytes)
        content_hash = hashlib.sha256(content).hexdigest()
        if len(content) != size or content_hash != row["content_hash"]:
            raise ToolError("hash_mismatch", "Prompt content does not match its stored source identity.")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            raise ToolError("invalid_encoding", "Prompt must be UTF-8 text.") from None
        return GitPromptEvidence(
            project_id=project_id, prompt_version_id=row["id"], commit_sha=sha,
            prompt_relpath=relpath, content=text, content_hash=content_hash,
            source_ref=f"git:{sha}:{relpath}",
        )

    def read_git_prompt(self, project_id, commit_sha, prompt_relpath):
        def read():
            self._validate_sha(commit_sha)
            root = self._location(project_id, prompt_relpath)
            result = self._snapshot(project_id, commit_sha, prompt_relpath, root)
            return result, [f"prompt:{result.prompt_version_id}", f"git:{commit_sha}"]
        return self._invoke(project_id, "read_git_prompt", read)

    def compare_prompt_versions(self, project_id, base_sha, target_sha, prompt_relpath):
        def compare():
            self._validate_sha(base_sha)
            self._validate_sha(target_sha)
            root = self._location(project_id, prompt_relpath)
            base = self._snapshot(project_id, base_sha, prompt_relpath, root)
            target = self._snapshot(project_id, target_sha, prompt_relpath, root)
            diff = self._git(root, ["diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                                    "--no-color", "--text", "--no-prefix", "--unified=3",
                                    base_sha, target_sha, "--", prompt_relpath], self.max_diff_bytes).decode("utf-8")
            result = GitDiffEvidence(
                project_id=project_id, base_version_id=base.prompt_version_id,
                target_version_id=target.prompt_version_id, base_sha=base_sha, target_sha=target_sha,
                prompt_relpath=prompt_relpath, diff_text=diff, source_refs=[base.source_ref, target.source_ref],
            )
            return result, [f"prompt:{base.prompt_version_id}", f"prompt:{target.prompt_version_id}"]
        return self._invoke(project_id, "compare_prompt_versions", compare)
