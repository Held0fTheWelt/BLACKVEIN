"""Governance runtime source segment: route_listing_and_readiness_helpers.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
                authenticated = status not in {401, 403}
                usable = False
                health_status = "failing" if status in {401, 403} else "degraded"
                error_code = "auth_failed" if status in {401, 403} else f"http_{status}"
                error_message = f"Provider responded with HTTP {status}."
            except URLError as e:
                latency_ms = int((perf_counter() - started) * 1000)
                reachable = False
                authenticated = False
                usable = False
                health_status = "failing"
                error_code = "network_unreachable"
                error_message = str(e.reason) if getattr(e, "reason", None) else "Provider endpoint unreachable."
            except Exception as e:  # pragma: no cover - defensive
                latency_ms = int((perf_counter() - started) * 1000)
                reachable = False
                authenticated = False
                usable = False
                health_status = "failing"
                error_code = "health_check_failed"
                error_message = str(e)
    provider.health_status = health_status
    provider.last_tested_at = tested_at
    db.session.add(
        ProviderHealthCheck(
            health_check_id=f"health_{uuid4().hex}",
            provider_id=provider_id,
            health_status=health_status,
            latency_ms=latency_ms,
            error_code=error_code,
            error_message=error_message,
            tested_at=tested_at,
        )
    )
    _audit(
        "provider_health_tested",
        "ai_runtime",
        provider_id,
        actor,
        "Provider health test executed.",
        {"health_status": health_status, "error_code": error_code},
    )
    db.session.commit()
    return {
        "provider_id": provider_id,
        "provider_type": provider.provider_type,
        "health_status": health_status,
        "reachable": reachable,
        "authenticated": authenticated,
        "credential_configured": bool(provider.credential_configured),
        "usable": usable,
        "latency_ms": latency_ms,
        "error_code": error_code,
        "operator_message": error_message or "Provider is usable.",
        "health_check_strategy": contract.get("health_check_strategy"),
        "tested_at": tested_at.isoformat(),
    }


def list_models() -> list[dict]:
    rows = AIModelConfig.query.order_by(AIModelConfig.model_id.asc()).all()
    providers = {p.provider_id: p for p in AIProviderConfig.query.all()}

    def _provider_runtime_eligible(provider: AIProviderConfig | None) -> bool:
        if provider is None:
            return False
        contract = _provider_contract(provider.provider_type)
        requires_credential = bool(contract.get("requires_credential"))
        return bool(
            provider.is_enabled
            and (not requires_credential or provider.credential_configured)
            and provider.health_status not in {"failing", "disabled"}
'''
