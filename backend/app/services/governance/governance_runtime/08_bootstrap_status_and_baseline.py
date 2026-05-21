"""Governance runtime source segment: bootstrap_status_and_baseline.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
                }
            return {
                "success": True,
                "content": content,
                "metadata": metadata,
                "error_code": None,
                "operator_message": "Model responded successfully.",
            }
    except httpx.HTTPStatusError as exc:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
        metadata["http_status"] = status
        excerpt = openai_http_error_excerpt(response)
        if excerpt:
            metadata["provider_error_excerpt"] = excerpt
        msg = f"Provider responded with HTTP {status}." if status else str(exc)
        if excerpt:
            msg = f"{msg} {excerpt}"
        return {
            "success": False,
            "content": "",
            "metadata": metadata,
            "error_code": f"http_{status}" if status else "http_status_error",
            "operator_message": msg,
        }
    except httpx.HTTPError as exc:
        metadata["error_type"] = type(exc).__name__
        return {
            "success": False,
            "content": "",
            "metadata": metadata,
            "error_code": type(exc).__name__,
            "operator_message": str(exc),
        }


def _attempt_runtime_rebind() -> dict[str, object]:
    rebind: dict[str, object] = {"attempted": False, "skipped": True}
    try:
        from app.services.game.game_service import has_complete_play_service_config, reload_play_story_runtime_governed_config

        if has_complete_play_service_config():
            rebind["attempted"] = True
            rebind["skipped"] = False
            rebind.update(reload_play_story_runtime_governed_config())
    except Exception as exc:  # noqa: BLE001 — operator-facing best-effort rebind must not fail the write
        rebind["attempted"] = True
        rebind["skipped"] = False
        rebind["ok"] = False
        rebind["error"] = str(exc)[:500]
    return rebind


def _audit(event_type: str, scope: str, target_ref: str, changed_by: str, summary: str, metadata: dict | None = None) -> None:
    db.session.add(
        SettingAuditEvent(
            audit_event_id=f"audit_{uuid4().hex}",
            event_type=event_type,
            scope=scope,
            target_ref=target_ref,
            changed_by=changed_by,
            summary=summary,
            metadata_json=metadata or {},
        )
    )


def _seed_default_presets() -> None:
    for preset_payload in _DEFAULT_PRESETS:
        if db.session.get(BootstrapPreset, preset_payload["preset_id"]) is not None:
            continue
        db.session.add(BootstrapPreset(**preset_payload, is_builtin=True))
'''
