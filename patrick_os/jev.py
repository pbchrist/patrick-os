"""TypeSafe/Jev semantic gates for compact Patrick OS decisions.

Known facts and execution authority stay in code. Jev is used only where semantic
judgment helps: policy interpretation, fit, personalization specificity, and draft
quality. Batch evaluation expands one phase's questions across many compact items
and sends them in one System One request.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .skills import root

DEFAULT_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
RETRYABLE_STATUS = {429, 529}


class JevError(RuntimeError):
    pass


def configured() -> bool:
    return bool(os.getenv("TYPESAFE_API_KEY", "").strip())


def profile_path(name: str, base=None) -> Path:
    return root(base) / "config" / f"{name}-jev.json"


def load_profile(name: str, base=None) -> dict:
    path = profile_path(name, base)
    if not path.is_file():
        raise JevError(f"no Jev profile at {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise JevError(f"invalid Jev profile {path}: {exc}") from exc
    phases = data.get("phases") or {}
    if not phases:
        raise JevError(f"Jev profile {path} declares no phases")
    return data


def _question_payload(spec: dict, item_index: int) -> dict:
    allowed = {"type", "instructions", "criteria"}
    question = {k: v for k, v in spec.items() if k in allowed}
    original = question.get("instructions")
    question["instructions"] = {
        "scope": f"Evaluate only the reviewer/work item at `items[{item_index}]`.",
        "question": original,
    }
    return question


def _items(state) -> list[dict]:
    if isinstance(state, dict):
        return [state]
    if isinstance(state, list) and all(isinstance(item, dict) for item in state):
        return state
    raise JevError("state must be a JSON object or an array of JSON objects")


def build_request(profile: dict, phase: str, state) -> tuple[dict, dict]:
    phase_spec = (profile.get("phases") or {}).get(phase)
    if phase_spec is None:
        raise JevError(f"unknown Jev phase {phase!r}")
    items = _items(state)
    max_items = int(profile.get("max_batch_items", 20))
    if len(items) > max_items:
        raise JevError(f"batch has {len(items)} items; maximum is {max_items}")

    questions = {}
    immediate = {}
    mapping = {}
    templates = phase_spec.get("questions") or {}
    for index, item in enumerate(items):
        blockers = [str(x) for x in (item.get("deterministic_blockers") or []) if str(x)]
        if blockers:
            immediate[index] = {
                "verdict": "block",
                "deterministic_blockers": blockers,
                "questions": {},
            }
            continue
        for name, spec in templates.items():
            qid = f"i{index:03d}__{name}"
            questions[qid] = _question_payload(spec, index)
            mapping[qid] = (index, name, spec)
    payload = {
        "state": {"items": items},
        "model": profile.get("model", DEFAULT_MODEL),
        "questions": questions,
    }
    meta = {"items": items, "mapping": mapping, "immediate": immediate, "phase_spec": phase_spec}
    return payload, meta


def _http(payload: dict, *, api_key: str, endpoint: str, timeout: int, retries: int) -> dict:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            if exc.code in RETRYABLE_STATUS and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise JevError(f"TypeSafe HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise JevError(f"TypeSafe request failed: {type(exc).__name__}: {exc}") from exc
    raise JevError("TypeSafe request failed")


def evaluate(payload: dict, *, api_key=None, endpoint=None, timeout=30, retries=2, transport=None):
    if not payload.get("questions"):
        return {"model": payload.get("model", DEFAULT_MODEL), "answers": {}, "usage": {}}
    if transport is not None:
        result = transport(payload)
    else:
        key = (api_key or os.getenv("TYPESAFE_API_KEY", "")).strip()
        if not key:
            raise JevError("TYPESAFE_API_KEY is not configured; Jev gate fails closed")
        url = endpoint or os.getenv("TYPESAFE_SYSTEMONE_URL", DEFAULT_ENDPOINT)
        result = _http(payload, api_key=key, endpoint=url, timeout=timeout, retries=retries)
    if not isinstance(result, dict) or not isinstance(result.get("answers"), dict):
        raise JevError("TypeSafe response has no answers map")
    return result


def _classify(answer: dict, spec: dict) -> tuple[str, float | str | None]:
    kind = spec.get("type")
    if answer.get("type") != kind:
        return "block", None
    if kind == "noul":
        value = float(answer.get("noul", -1))
        pass_min = float(spec.get("pass_min", 0.8))
        review_min = float(spec.get("review_min", 0.55))
        return ("pass" if value >= pass_min else "review" if value >= review_min else "block"), value
    if kind == "score":
        value = float(answer.get("score", -1))
        pass_min = float(spec.get("pass_min", 1.0))
        review_min = float(spec.get("review_min", 0.5))
        return ("pass" if value >= pass_min else "review" if value >= review_min else "block"), value
    if kind == "choice":
        value = answer.get("choice")
        if value in (spec.get("pass_choices") or []):
            return "pass", value
        if value in (spec.get("review_choices") or []):
            return "review", value
        return "block", value
    return "block", None


def gate(profile_name: str, phase: str, state, *, execute=False, base=None, transport=None) -> dict:
    profile = load_profile(profile_name, base)
    payload, meta = build_request(profile, phase, state)
    result = {
        "profile": profile_name,
        "profile_version": profile.get("version"),
        "phase": phase,
        "mode": "execute" if execute else "dry-run",
        "model": payload["model"],
        "item_count": len(meta["items"]),
        "question_count": len(payload["questions"]),
        "configured": configured() or transport is not None,
    }
    if not execute:
        result["verdict"] = "block" if meta["immediate"] else "not_evaluated"
        result["items"] = [
            meta["immediate"].get(i, {"verdict": "not_evaluated", "deterministic_blockers": [], "questions": {}})
            for i in range(len(meta["items"]))
        ]
        result["question_ids"] = list(payload["questions"])
        return result

    response = evaluate(payload, transport=transport)
    answers = response.get("answers") or {}
    item_results = []
    for index in range(len(meta["items"])):
        if index in meta["immediate"]:
            item_results.append(meta["immediate"][index])
            continue
        qresults = {}
        statuses = []
        for qid, (mapped_index, name, spec) in meta["mapping"].items():
            if mapped_index != index:
                continue
            answer = answers.get(qid)
            if not isinstance(answer, dict):
                status, value = "block", None
                answer = {"error": "missing answer"}
            else:
                status, value = _classify(answer, spec)
            statuses.append(status)
            qresults[name] = {"verdict": status, "value": value, "answer": answer}
        verdict = "block" if "block" in statuses else "review" if "review" in statuses else "pass"
        item_results.append({"verdict": verdict, "deterministic_blockers": [], "questions": qresults})
    verdicts = [item["verdict"] for item in item_results]
    result["verdict"] = "block" if "block" in verdicts else "review" if "review" in verdicts else "pass"
    result["items"] = item_results
    result["usage"] = response.get("usage") or {}
    result["resolved_model"] = response.get("model")
    return result
