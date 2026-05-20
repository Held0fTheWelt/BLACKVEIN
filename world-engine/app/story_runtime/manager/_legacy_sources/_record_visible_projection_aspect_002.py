SOURCE = r'''\
                    applicable=True,
                    status="partial",
                    expected={
                        **(
                            commit_record.get("expected")
                            if isinstance(commit_record, dict) and isinstance(commit_record.get("expected"), dict)
                            else {}
                        ),
                        "contractually_required_beat_recorded": True,
                    },
                    actual={
                        **(
                            commit_record.get("actual")
                            if isinstance(commit_record, dict) and isinstance(commit_record.get("actual"), dict)
                            else {}
                        ),
                        "required_beat_lost": True,
                        "selected_beat": selected.get("selected_beat_id"),
                    },
                    reasons=[beat_failure_reason],
                    source="commit",
                    failure_class=beat_failure_class,
                    failure_reason=beat_failure_reason,
                    selected_beat=selected.get("selected_beat_id"),
                    lost_at_stage="visible_projection",
                ),
            )
    return out
'''
