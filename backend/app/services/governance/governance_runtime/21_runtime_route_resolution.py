"""Governance runtime source segment: runtime_route_resolution.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
                contract=contract,
                secret=secret,
                model=model,
                timeout_seconds=float(model.timeout_seconds or 10),
                provider_type=provider.provider_type,
            )
            result = None
            success = bool(probe.get("success"))
            content = str(probe.get("content") or "").strip()
            metadata = probe.get("metadata") if isinstance(probe.get("metadata"), dict) else {}
            error_code = probe.get("error_code")
            operator_message = str(probe.get("operator_message") or ("Model responded successfully." if success else "Model probe failed."))
        else:
            result = adapter.generate(
                "Reply with OK.",
                timeout_seconds=float(model.timeout_seconds or 10),
                model_name=model.model_name,
            )
            success = bool(getattr(result, "success", False))
            content = str(getattr(result, "content", "") or "").strip()
            metadata = getattr(result, "metadata", {}) or {}
            error_code = None if success else "model_test_unsuccessful"
            operator_message = "Model responded successfully." if success else "Model call completed but did not report success."
        latency_ms = int((perf_counter() - started) * 1000)
    except Exception as exc:  # noqa: BLE001 — operator-facing probe
        latency_ms = int((perf_counter() - started) * 1000)
        success = False
        content = ""
        metadata = {}
        error_code = type(exc).__name__
        operator_message = str(exc)

    _audit(
        "model_tested",
        "ai_runtime",
        model_id,
        actor,
        "Model test executed.",
        {"success": success, "provider_id": provider.provider_id, "error_code": error_code},
    )
    db.session.commit()
    return {
        "model_id": model_id,
        "provider_id": provider.provider_id,
        "provider_type": provider.provider_type,
        "model_name": model.model_name,
        "success": success,
        "available": success,
        "latency_ms": latency_ms,
        "error_code": error_code,
        "operator_message": operator_message,
        "response_excerpt": content[:200] if content else "",
        "metadata": metadata if isinstance(metadata, dict) else {},
    }


def list_routes() -> list[dict]:
    rows = AITaskRoute.query.order_by(AITaskRoute.route_id.asc()).all()
    model_rows = {m.model_id: m for m in AIModelConfig.query.all()}
    provider_rows = {p.provider_id: p for p in AIProviderConfig.query.all()}

    def _model_runtime_eligible(
        model_id: str | None,
        *,
        route_field: str,
        task_kind: str | None,
        route_id: str | None,
    ) -> tuple[bool, str | None]:
        if not model_id:
            return False, "model_reference_missing"
        model = model_rows.get(model_id)
        if model is None:
'''
