from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _extract_notebook_cells(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(_read_text(path))
    cells = payload.get("cells", [])
    ordered: list[dict[str, Any]] = []
    for idx, cell in enumerate(cells):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", [])
        code = ""
        if isinstance(source, list):
            code = "".join(source)
        elif isinstance(source, str):
            code = source
        ordered.append({"cell_index": idx, "code": code})
    return ordered


def _extract_notebook_code(path: Path) -> str:
    cells = _extract_notebook_cells(path)
    return "\n\n".join([cell["code"] for cell in cells])


def _collect_files(root: Path, max_files: int) -> list[Path]:
    if root.is_file():
        return [root]
    files = sorted(
        [p for p in root.rglob("*") if p.suffix in {".py", ".ipynb"}]
    )
    return files[:max_files]


def _summarize_code(code: str) -> dict[str, Any]:
    import_re = re.compile(r"^(from\s+\S+\s+import\s+.+|import\s+.+)$")
    def_re = re.compile(r"^(def|class)\s+([A-Za-z_][\w]*)")
    imports: list[str] = []
    functions: list[str] = []
    classes: list[str] = []
    has_main = False

    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("if __name__") and "__main__" in stripped:
            has_main = True
        match = def_re.match(stripped)
        if match:
            if match.group(1) == "def":
                functions.append(match.group(2))
            else:
                classes.append(match.group(2))
        if import_re.match(stripped):
            imports.append(stripped)

    return {
        "imports": imports[:15],
        "functions": functions[:20],
        "classes": classes[:20],
        "has_main": has_main,
    }


def _get_call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _get_call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return _get_call_name(node.func)
    return ""


def _extract_string_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_list_literals(node: ast.AST) -> list[str]:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values: list[str] = []
        for item in node.elts:
            value = _extract_string_literal(item)
            if value is not None:
                values.append(value)
        return values
    return []


def _extract_path_from_call(call: ast.Call) -> str | None:
    for arg in call.args:
        value = _extract_string_literal(arg)
        if value is not None:
            return value
    for keyword in call.keywords:
        if keyword.arg in {"path", "file", "filename", "filepath", "filepath_or_buffer", "source"}:
            value = _extract_string_literal(keyword.value)
            if value is not None:
                return value
    return None


def _looks_like_model_name(name: str) -> bool:
    model_markers = (
        "classifier",
        "regressor",
        "regression",
        "randomforest",
        "xgb",
        "lgbm",
        "catboost",
        "lightgbm",
        "xgboost",
        "logisticregression",
        "linearregression",
        "svm",
        "svc",
        "knn",
        "kneighbors",
        "mlp",
        "transformer",
        "lstm",
        "gru",
        "bert",
    )
    lowered = name.lower()
    return any(marker in lowered for marker in model_markers)


def _safe_parse_ast(code: str) -> ast.AST | None:
    try:
        return ast.parse(code)
    except SyntaxError:
        return None


def _extract_function_snippets(code: str, max_lines: int = 50) -> list[dict[str, Any]]:
    snippets: list[dict[str, Any]] = []
    lines = code.splitlines()
    tree = _safe_parse_ast(code)
    if tree is None:
        return snippets
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name.lower() not in {"train", "main", "run", "fit", "predict"}:
                continue
            start = max(node.lineno - 1, 0)
            end = min(start + max_lines, len(lines))
            snippet = "\n".join(lines[start:end])
            snippets.append(
                {
                    "symbol": f"def {node.name}",
                    "start_line": node.lineno,
                    "snippet": snippet,
                }
            )
    return snippets


def _extract_core_logic(code: str, max_lines: int = 120) -> list[dict[str, Any]]:
    snippets: list[dict[str, Any]] = []
    lines = code.splitlines()
    tree = _safe_parse_ast(code)
    if tree is None:
        return snippets
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name.lower() not in {"train", "fit", "predict", "inference"}:
                continue
            start = max(node.lineno - 1, 0)
            end = min(start + max_lines, len(lines))
            snippet = "\n".join(lines[start:end])
            snippets.append(
                {
                    "symbol": f"def {node.name}",
                    "start_line": node.lineno,
                    "snippet": snippet,
                }
            )
    return snippets


def _find_local_imports(code: str) -> list[str]:
    tree = _safe_parse_ast(code)
    if tree is None:
        return []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        if isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _resolve_local_imports(base_dir: Path, imports: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for module in imports:
        parts = module.split(".")
        if not parts:
            continue
        candidate_py = base_dir / ("/".join(parts) + ".py")
        candidate_init = base_dir / "/".join(parts) / "__init__.py"
        if candidate_py.exists():
            resolved.append(candidate_py)
        elif candidate_init.exists():
            resolved.append(candidate_init)
    return resolved


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _analyze_ast(code: str) -> dict[str, Any]:
    tree = _safe_parse_ast(code)
    if tree is None:
        return {
            "data_sources": [],
            "feature_sets": [],
            "target_variables": [],
            "model_definitions": [],
            "pipeline_steps": [],
            "training_calls": [],
            "prediction_calls": [],
            "evaluation_calls": [],
            "report_outputs": [],
        }

    data_sources: list[str] = []
    feature_sets: list[str] = []
    target_variables: list[str] = []
    model_definitions: list[str] = []
    pipeline_steps: list[str] = []
    training_calls: list[str] = []
    prediction_calls: list[str] = []
    evaluation_calls: list[str] = []
    report_outputs: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _get_call_name(node.func)
            if not call_name:
                continue
            path_literal = _extract_path_from_call(node)
            if any(
                key in call_name
                for key in (
                    "read_csv",
                    "read_parquet",
                    "read_excel",
                    "read_json",
                    "read_table",
                    "read_sql",
                    "read_pickle",
                    "read_feather",
                    "open",
                    "joblib.load",
                )
            ):
                data_sources.append(
                    f"{call_name} -> {path_literal or '(unknown path)'}"
                )
            if "spark.read" in call_name:
                data_sources.append(f"{call_name} -> {path_literal or '(unknown source)'}")
            if _looks_like_model_name(call_name):
                model_definitions.append(call_name)
            if call_name.endswith("Pipeline") or call_name.endswith("ColumnTransformer"):
                pipeline_steps.append(call_name)
            if call_name.endswith(".fit"):
                training_calls.append(call_name)
            if call_name.endswith(".predict") or call_name.endswith(".predict_proba"):
                prediction_calls.append(call_name)
            if call_name.endswith(".score") or "evaluate" in call_name.lower():
                evaluation_calls.append(call_name)
            if any(
                call_name.endswith(suffix)
                for suffix in (".to_csv", ".to_json", ".to_excel", ".save", ".savefig", ".dump")
            ):
                report_outputs.append(call_name)

        if isinstance(node, ast.Assign):
            targets = [t for t in node.targets if isinstance(t, ast.Name)]
            for target in targets:
                name = target.id.lower()
                if name in {
                    "features",
                    "feature_cols",
                    "feature_columns",
                    "x_cols",
                    "x_columns",
                    "input_features",
                }:
                    literals = _extract_list_literals(node.value)
                    if literals:
                        feature_sets.append(", ".join(literals))
                if name in {"target", "target_col", "target_column", "label", "y"}:
                    literal = _extract_string_literal(node.value)
                    if literal:
                        target_variables.append(literal)
                if name in {"x", "x_train"} and isinstance(node.value, ast.Subscript):
                    literals = _extract_list_literals(node.value.slice)  # type: ignore[arg-type]
                    if literals:
                        feature_sets.append(", ".join(literals))

    return {
        "data_sources": data_sources,
        "feature_sets": feature_sets,
        "target_variables": target_variables,
        "model_definitions": model_definitions,
        "pipeline_steps": pipeline_steps,
        "training_calls": training_calls,
        "prediction_calls": prediction_calls,
        "evaluation_calls": evaluation_calls,
        "report_outputs": report_outputs,
    }


def analyze_code_logic(
    *,
    path: str,
    max_files: int = 20,
    max_chars: int = 200000,
    max_depth: int = 1,
) -> dict[str, Any]:
    """
    Analyze Python or Jupyter files to infer the logic flow.

    Args:
        path: File or directory path to analyze.
        max_files: Maximum number of files to scan in a directory.
        max_chars: Max characters per file used for analysis.
        max_depth: Import recursion depth for local modules.

    Returns:
        A dict with files analyzed, step-by-step reasoning, and notes.
    """
    target = Path(path).expanduser()
    if not target.exists():
        return {"error": f"Path not found: {target}"}

    files = _collect_files(target, max_files=max_files)
    if not files:
        return {"error": "No .py or .ipynb files found."}

    scanned: set[Path] = set()
    queue: list[tuple[Path, int]] = [(file_path, 0) for file_path in files]
    ordered_cells: list[dict[str, Any]] = []
    all_cells: list[dict[str, Any]] = []
    snippets: list[dict[str, Any]] = []
    core_logic: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    deep_dive = {
        "data_sources": [],
        "feature_sets": [],
        "target_variables": [],
        "model_definitions": [],
        "pipeline_steps": [],
        "training_calls": [],
        "prediction_calls": [],
        "evaluation_calls": [],
        "report_outputs": [],
    }
    truncated_files: list[str] = []
    while queue and len(scanned) < max_files:
        file_path, depth = queue.pop(0)
        if file_path in scanned:
            continue
        scanned.add(file_path)
        if file_path.suffix == ".ipynb":
            cells = _extract_notebook_cells(file_path)
            for cell in cells:
                if not cell["code"].strip():
                    continue
                code_lines = cell["code"].splitlines()
                snippet = "\n".join(code_lines[:50])
                lowered = cell["code"].lower()
                all_cells.append(
                    {
                        "file": str(file_path),
                        "cell_index": cell["cell_index"],
                        "snippet": snippet,
                        "keyword_hit": any(
                            key in lowered for key in ("fit(", "predict", "target")
                        ),
                    }
                )
            code = "\n\n".join([cell["code"] for cell in cells])
        else:
            code = _read_text(file_path)
        if len(code) > max_chars:
            code = code[:max_chars]
            truncated_files.append(str(file_path))
        summary = _summarize_code(code)
        summary["file"] = str(file_path)
        summaries.append(summary)
        ast_summary = _analyze_ast(code)
        for key in deep_dive:
            for item in ast_summary[key]:
                deep_dive[key].append(f"{file_path}: {item}")
        for snippet in _extract_function_snippets(code, max_lines=50):
            snippet["file"] = str(file_path)
            snippets.append(snippet)
        for snippet in _extract_core_logic(code, max_lines=120):
            snippet["file"] = str(file_path)
            core_logic.append(snippet)
        if depth < max_depth:
            imports = _find_local_imports(code)
            for resolved in _resolve_local_imports(file_path.parent, imports):
                queue.append((resolved, depth + 1))

    if all_cells:
        selected: list[dict[str, Any]] = []
        selected_keys: set[tuple[str, int]] = set()
        for cell in all_cells[:5]:
            key = (cell["file"], cell["cell_index"])
            if key in selected_keys:
                continue
            selected_keys.add(key)
            selected.append(cell)
        for cell in all_cells:
            if not cell.get("keyword_hit"):
                continue
            key = (cell["file"], cell["cell_index"])
            if key in selected_keys:
                continue
            selected_keys.add(key)
            selected.append(cell)
        ordered_cells = [
            {"file": item["file"], "cell_index": item["cell_index"], "snippet": item["snippet"]}
            for item in selected
        ]

    for key in deep_dive:
        deep_dive[key] = _dedupe_preserve_order(deep_dive[key])

    steps: list[str] = [
        "Extract core training and prediction logic from functions.",
        "Preserve notebook execution order to reconstruct workflow.",
        "Collect data sources, features, targets, and model definitions.",
    ]

    notes = "This is a heuristic summary based on static parsing."
    if truncated_files:
        notes += " Some files were truncated for size."

    return {
        "files": [item["file"] for item in summaries],
        "steps": steps,
        "summaries": summaries,
        "deep_dive": deep_dive,
        "snippets": snippets,
        "core_logic": core_logic,
        "ordered_cells": ordered_cells,
        "truncated_files": truncated_files,
        "notes": notes,
    }


__all__ = ["analyze_code_logic"]
