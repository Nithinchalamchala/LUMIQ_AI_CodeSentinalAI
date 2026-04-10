"""Git operations tool for repository management."""

import os
import shutil
import tempfile
import difflib
from pathlib import Path


class GitTools:
    """Handles Git operations: cloning, diffing, and workspace management."""

    def __init__(self):
        self.name = "git_tools"

    def clone_repo(self, repo_url: str, dest_dir: str = None) -> str:
        """Clone a Git repository to a local directory."""
        if dest_dir is None:
            dest_dir = tempfile.mkdtemp(prefix="codereview_")

        try:
            import git
            git.Repo.clone_from(repo_url, dest_dir, depth=1)
            return dest_dir
        except Exception as e:
            raise RuntimeError(f"Failed to clone repository: {e}")

    def create_workspace(self, source_path: str, workspace_dir: str = None) -> str:
        """Create a working copy of a project directory."""
        if workspace_dir is None:
            workspace_dir = tempfile.mkdtemp(prefix="codereview_ws_")

        if os.path.exists(workspace_dir):
            shutil.rmtree(workspace_dir)

        shutil.copytree(
            source_path, workspace_dir,
            ignore=shutil.ignore_patterns(
                '__pycache__', '.git', '.env', 'node_modules',
                '*.pyc', '.venv', 'venv'
            )
        )
        return workspace_dir

    def generate_diff(self, original_content: str, modified_content: str,
                      file_path: str = "file.py") -> str:
        """Generate a unified diff between original and modified content."""
        original_lines = original_content.splitlines(keepends=True)
        modified_lines = modified_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines, modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=""
        )
        return "\n".join(diff)

    def generate_file_diff(self, original_path: str, modified_path: str) -> str:
        """Generate diff between two file paths."""
        try:
            with open(original_path, 'r', encoding='utf-8') as f:
                original = f.read()
            with open(modified_path, 'r', encoding='utf-8') as f:
                modified = f.read()
            return self.generate_diff(original, modified, os.path.basename(modified_path))
        except IOError as e:
            return f"Error reading files: {e}"

    def get_project_files(self, project_path: str, extension: str = ".py") -> list[str]:
        """Get all files with a given extension in a project."""
        files = []
        for root, _, filenames in os.walk(project_path):
            if any(part.startswith('.') or part in ('__pycache__', 'node_modules', 'venv')
                   for part in Path(root).parts):
                continue
            for f in filenames:
                if f.endswith(extension):
                    files.append(os.path.join(root, f))
        return sorted(files)

    def cleanup_workspace(self, workspace_dir: str):
        """Remove a temporary workspace."""
        if os.path.exists(workspace_dir) and "codereview_" in workspace_dir:
            shutil.rmtree(workspace_dir, ignore_errors=True)
