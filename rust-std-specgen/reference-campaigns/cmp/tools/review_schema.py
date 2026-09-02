"""Strict parsing helpers for reviewer-owned acceptance records."""

from __future__ import annotations

from typing import Any


def artifact_binding_map(value: Any) -> dict[str, str] | None:
    """Return unique path/hash bindings, or ``None`` for malformed input."""

    if not isinstance(value, list):
        return None
    result: dict[str, str] = {}
    for item in value:
        if not isinstance(item, dict):
            return None
        path = item.get("path")
        digest = item.get("sha256")
        if not isinstance(path, str) or not path:
            return None
        if not isinstance(digest, str) or not digest:
            return None
        if path in result:
            return None
        result[path] = digest
    return result


def question_verdict_map(value: Any) -> dict[str, str] | None:
    """Return unique question/verdict pairs, or ``None`` if any row is bad."""

    if not isinstance(value, list):
        return None
    result: dict[str, str] = {}
    for item in value:
        if not isinstance(item, dict):
            return None
        question = item.get("question")
        verdict = item.get("verdict")
        if not isinstance(question, str) or not question:
            return None
        if not isinstance(verdict, str) or not verdict:
            return None
        if question in result:
            return None
        result[question] = verdict
    return result
