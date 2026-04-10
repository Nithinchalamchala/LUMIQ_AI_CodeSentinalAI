"""AST-based Python code parser and structural analyzer."""

import ast
import os
from typing import Optional
from backend.models import Issue, Severity, IssueCategory


class CodeParser:
    """Parses Python source files using the AST module to detect structural issues."""

    def __init__(self):
        self.name = "code_parser"

    def analyze_file(self, file_path: str) -> list[Issue]:
        """Analyze a single Python file for structural issues."""
        issues = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()
        except (IOError, OSError) as e:
            return [Issue(
                file_path=file_path, line_number=0, severity=Severity.HIGH,
                category=IssueCategory.BUG, title="File read error",
                description=str(e), source=self.name
            )]

        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError as e:
            return [Issue(
                file_path=file_path, line_number=e.lineno or 0,
                severity=Severity.CRITICAL, category=IssueCategory.BUG,
                title="Syntax Error", description=str(e),
                code_snippet=e.text or "", source=self.name
            )]

        lines = source.splitlines()
        issues.extend(self._check_unused_imports(tree, source, file_path))
        issues.extend(self._check_bare_except(tree, file_path, lines))
        issues.extend(self._check_mutable_defaults(tree, file_path, lines))
        issues.extend(self._check_missing_return(tree, file_path, lines))
        issues.extend(self._check_global_variables(tree, file_path, lines))
        issues.extend(self._check_eval_usage(tree, file_path, lines))
        issues.extend(self._check_too_many_arguments(tree, file_path, lines))

        return issues

    def analyze_directory(self, dir_path: str) -> list[Issue]:
        """Analyze all Python files in a directory."""
        all_issues = []
        for root, _, files in os.walk(dir_path):
            # Skip hidden dirs and __pycache__
            if any(part.startswith('.') or part == '__pycache__' for part in root.split(os.sep)):
                continue
            for fname in files:
                if fname.endswith(".py"):
                    fpath = os.path.join(root, fname)
                    all_issues.extend(self.analyze_file(fpath))
        return all_issues

    def _get_snippet(self, lines: list[str], lineno: int, context: int = 1) -> str:
        """Get a code snippet around a line number."""
        start = max(0, lineno - 1 - context)
        end = min(len(lines), lineno + context)
        return "\n".join(lines[start:end])

    def _check_unused_imports(self, tree: ast.AST, source: str, file_path: str) -> list[Issue]:
        """Detect imported names that are never used in the code."""
        issues = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports.append((name, alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports.append((name, f"{node.module}.{alias.name}", node.lineno))

        # Check which imports are used (simple text search — handles most cases)
        for local_name, full_name, lineno in imports:
            # Count occurrences (subtract the import line itself)
            count = source.count(local_name)
            if count <= 1:
                issues.append(Issue(
                    file_path=file_path, line_number=lineno,
                    severity=Severity.LOW, category=IssueCategory.STYLE,
                    title=f"Unused import: {full_name}",
                    description=f"The import '{full_name}' appears to be unused.",
                    suggested_fix=f"Remove the unused import: {full_name}",
                    source=self.name
                ))
        return issues

    def _check_bare_except(self, tree: ast.AST, file_path: str, lines: list[str]) -> list[Issue]:
        """Detect bare except clauses (except without specifying exception type)."""
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append(Issue(
                    file_path=file_path, line_number=node.lineno,
                    severity=Severity.MEDIUM, category=IssueCategory.BEST_PRACTICE,
                    title="Bare except clause",
                    description="Using bare 'except:' catches all exceptions including SystemExit and KeyboardInterrupt. Use 'except Exception:' instead.",
                    code_snippet=self._get_snippet(lines, node.lineno),
                    suggested_fix="Replace 'except:' with 'except Exception:'",
                    source=self.name
                ))
        return issues

    def _check_mutable_defaults(self, tree: ast.AST, file_path: str, lines: list[str]) -> list[Issue]:
        """Detect mutable default arguments in function definitions."""
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append(Issue(
                            file_path=file_path, line_number=node.lineno,
                            severity=Severity.HIGH, category=IssueCategory.BUG,
                            title=f"Mutable default argument in '{node.name}'",
                            description="Mutable default arguments are shared between all calls. This is a common Python gotcha that leads to unexpected behavior.",
                            code_snippet=self._get_snippet(lines, node.lineno),
                            suggested_fix="Use None as default and create the mutable object inside the function.",
                            source=self.name
                        ))
        return issues

    def _check_missing_return(self, tree: ast.AST, file_path: str, lines: list[str]) -> list[Issue]:
        """Detect functions that have some return paths with values and some without."""
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                returns = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
                if returns:
                    has_value = any(r.value is not None for r in returns)
                    has_bare = any(r.value is None for r in returns)
                    if has_value and has_bare:
                        issues.append(Issue(
                            file_path=file_path, line_number=node.lineno,
                            severity=Severity.MEDIUM, category=IssueCategory.BUG,
                            title=f"Inconsistent return in '{node.name}'",
                            description="Function has both explicit return values and bare returns, which implicitly return None.",
                            code_snippet=self._get_snippet(lines, node.lineno, 2),
                            suggested_fix="Ensure all return statements return a value or all return None explicitly.",
                            source=self.name
                        ))
        return issues

    def _check_global_variables(self, tree: ast.AST, file_path: str, lines: list[str]) -> list[Issue]:
        """Detect use of global keyword."""
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                issues.append(Issue(
                    file_path=file_path, line_number=node.lineno,
                    severity=Severity.LOW, category=IssueCategory.BEST_PRACTICE,
                    title=f"Global variable usage: {', '.join(node.names)}",
                    description="Using global variables makes code harder to test and reason about.",
                    code_snippet=self._get_snippet(lines, node.lineno),
                    suggested_fix="Consider using class attributes or passing values as function parameters.",
                    source=self.name
                ))
        return issues

    def _check_eval_usage(self, tree: ast.AST, file_path: str, lines: list[str]) -> list[Issue]:
        """Detect usage of eval() and exec() which are security risks."""
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in ("eval", "exec"):
                    issues.append(Issue(
                        file_path=file_path, line_number=node.lineno,
                        severity=Severity.CRITICAL, category=IssueCategory.SECURITY,
                        title=f"Dangerous {func_name}() usage",
                        description=f"Using {func_name}() can execute arbitrary code and is a serious security risk.",
                        code_snippet=self._get_snippet(lines, node.lineno),
                        suggested_fix=f"Replace {func_name}() with a safer alternative like ast.literal_eval() or explicit parsing.",
                        source=self.name
                    ))
        return issues

    def _check_too_many_arguments(self, tree: ast.AST, file_path: str, lines: list[str]) -> list[Issue]:
        """Detect functions with too many arguments (>5)."""
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args
                total = len(args.args) + len(args.kwonlyargs)
                # Subtract 'self' or 'cls'
                if args.args and args.args[0].arg in ('self', 'cls'):
                    total -= 1
                if total > 5:
                    issues.append(Issue(
                        file_path=file_path, line_number=node.lineno,
                        severity=Severity.LOW, category=IssueCategory.COMPLEXITY,
                        title=f"Too many arguments ({total}) in '{node.name}'",
                        description=f"Function has {total} parameters. Consider using a dataclass or configuration object.",
                        code_snippet=self._get_snippet(lines, node.lineno),
                        suggested_fix="Group related parameters into a dataclass or use **kwargs.",
                        source=self.name
                    ))
        return issues
