SOURCE = r'''\
            },
            "turn_aspect_ledger": ledger,
            "quality_class": QUALITY_CLASS_DEGRADED
            if output_fallback_used
            else QUALITY_CLASS_HEALTHY,
            "degradation_signals": [DEGRADATION_SIGNAL_FALLBACK_USED]
            if output_fallback_used
            else [],
            "degradation_summary": "; ".join(output_fallback_reasons)
            if output_fallback_used
            else "none",
            "phase_costs": phase_costs,
        }
'''
