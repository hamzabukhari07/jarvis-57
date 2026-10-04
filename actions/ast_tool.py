"""
actions/ast_tool.py — Structural Code AST Analysis & Search Tool.

Parses Python source files into abstract syntax trees to locate classes, functions,
imports, docstrings, and cyclomatic complexity hotspots without executing code.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _analyze_python_ast(content: str, path: str, op: str) -> Dict[str, Any]:
    try:
        tree = ast.parse(content, filename=path)
    except SyntaxError as e:
        return {"error": f"SyntaxError in {path} at line {e.lineno}: {e.msg}"}

    functions = []
    classes = []
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Estimate simple cyclomatic complexity
            branches = 1
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With, ast.Assert)):
                    branches += 1
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "async": isinstance(node, ast.AsyncFunctionDef),
                "args": [a.arg for a in node.args.args],
                "complexity": branches,
            })
        elif isinstance(node, ast.ClassDef):
            bases = [ast.unparse(b) for b in node.bases] if hasattr(ast, "unparse") else []
            classes.append({
                "name": node.name,
                "line": node.lineno,
                "bases": bases,
            })
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                imports.append(f"{mod}.{alias.name}" if mod else alias.name)

    return {
        "file": path,
        "functions_count": len(functions),
        "classes_count": len(classes),
        "imports_count": len(imports),
        "functions": functions,
        "classes": classes,
        "imports": imports[:30],
    }


def ast_tool(parameters: Dict[str, Any], **kwargs: Any) -> str:
    """
    Search and analyze Python codebase structure using AST.
    parameters = {
        "path": "core/task_manager.py",
        "op": "inspect" | "functions" | "classes" | "complexity"
    }
    """
    path_str = str(parameters.get("path") or "").strip()
    op = str(parameters.get("op") or "inspect").lower().strip()
    content = parameters.get("content")

    if not path_str and not content:
        return "Error: Either 'path' or 'content' is required."

    if path_str and not content:
        p = Path(path_str)
        if not p.exists():
            return f"Error: File not found: {path_str}"
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Error reading {path_str}: {e}"

    res = _analyze_python_ast(content, path_str or "<inline>", op)
    if "error" in res:
        return f"AST Error: {res['error']}"

    if op == "functions":
        fn_lines = [f"Functions in {path_str} ({res['functions_count']}):"]
        for f in res["functions"]:
            async_tag = "async " if f.get("async") else ""
            args_str = ", ".join(f.get("args", []))
            fn_lines.append(f"• L{f['line']}: {async_tag}{f['name']}({args_str}) [Complexity: {f['complexity']}]")
        return "\n".join(fn_lines) if res["functions"] else f"No function definitions found in {path_str}."

    if op == "classes":
        cls_lines = [f"Classes in {path_str} ({res['classes_count']}):"]
        for c in res["classes"]:
            bases_str = f"({', '.join(c['bases'])})" if c.get("bases") else ""
            cls_lines.append(f"• L{c['line']}: class {c['name']}{bases_str}")
        return "\n".join(cls_lines) if res["classes"] else f"No class definitions found in {path_str}."

    if op == "complexity":
        hotspots = sorted(res["functions"], key=lambda x: x["complexity"], reverse=True)
        high = [f for f in hotspots if f["complexity"] >= 10]
        if not high:
            return f"Clean code! All {len(res['functions'])} functions in {path_str} have cyclomatic complexity < 10."
        lines = [f"Complexity hotspots in {path_str} (>= 10 branches):"]
        for h in high:
            lines.append(f"• L{h['line']}: {h['name']}() -> Complexity {h['complexity']}")
        return "\n".join(lines)

    # Default: inspect summary
    return (
        f"AST Structure for {path_str}:\n"
        f"• Classes ({res['classes_count']}): {', '.join(c['name'] for c in res['classes'][:10]) or 'None'}\n"
        f"• Functions ({res['functions_count']}): {', '.join(f['name'] for f in res['functions'][:15]) or 'None'}\n"
        f"• Imports ({res['imports_count']}): {', '.join(res['imports'][:10]) or 'None'}"
    )


TOOL = {
    "name": "ast_tool",
    "description": (
        "Structural Python code parser and AST analyzer. "
        "Inspects functions, classes, arguments, and calculates cyclomatic complexity hotspots for any file or code snippet. "
        "Use op='inspect', 'functions', 'classes', or 'complexity'."
    ),
    "risk": "read_only",
    "enabled": True,
    "behavior": "BLOCKING",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "Path to Python source file.",
            },
            "op": {
                "type": "STRING",
                "enum": ["inspect", "functions", "classes", "complexity"],
                "description": "Operation to perform on AST (default 'inspect').",
            },
            "content": {
                "type": "STRING",
                "description": "Optional inline Python code string to parse instead of reading from file path.",
            },
        },
        "required": [],
    },
    "handler": ast_tool,
}

handler = ast_tool
