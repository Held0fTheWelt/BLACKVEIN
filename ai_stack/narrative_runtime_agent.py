"""
NarrativeRuntimeAgent: Event-based narrator streaming for Live Dramatic Scene Simulator.

This module provides the core streaming narrator component that runs after LDSS,
generating continuous narrator blocks based on NPC motivation pressure and signaling
ruhepunkt (rest point) when NPC initiatives are exhausted.

Architecture:
- Event-based runtime (not turn-sequential)
- Narrator streams continuously based on motivation pressure
- Input blocked while streaming (queued for ruhepunkt processing)
- Optional Langfuse tracing (JSON scaffold default)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generator, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Narrator validation patterns (Phase 2: aligned with LDSS narrator voice contract)
_NARRATOR_DIALOGUE_SUMMARY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(argue|discuss|debate|argue about)\b", re.IGNORECASE),
    re.compile(r"\b(Véronique|Veronique|Alain|Michel|Annette)\s+(and|says?|told|ask)\b", re.IGNORECASE),
    re.compile(r"\bwhile\s+\w+\s+becomes?\s+\b", re.IGNORECASE),
]

_NARRATOR_FORCED_STATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bYou\s+(decide|feel|know|realize|understand|think|believe)\s+that\b", re.IGNORECASE),
    re.compile(r"\bYou\s+(are|were)\s+(right|wrong|ashamed|angry|happy)\b", re.IGNORECASE),
]

_NARRATOR_HIDDEN_INTENT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b\w+\s+(secretly|actually|really|truly)\s+(wants?|plans?|intends?)\b", re.IGNORECASE),
    re.compile(r"\bYou\s+can\s+see\s+through\s+\w+\b", re.IGNORECASE),
]

# Valid narrator voice patterns (observational, not forced)
_NARRATOR_OBSERVATIONAL_PATTERNS: list[str] = [
    "notice", "observe", "witness", "perceive", "sense", "detect",
    "pause", "shift", "hesitation", "tension", "pressure",
    "atmosphere", "weight", "silence", "undertone",
]


class NarrativeEventKind(Enum):
    """Event types emitted by NarrativeRuntimeAgent."""
    NARRATOR_BLOCK = "narrator_block"
    RUHEPUNKT_REACHED = "ruhepunkt_reached"
    STREAMING_COMPLETE = "streaming_complete"
    ERROR = "error"
    TRACE_SCAFFOLD_EMITTED = "trace_scaffold_emitted"  # Phase 6: tracing disabled signal
    TRACE_SCAFFOLD_SUMMARY = "trace_scaffold_summary"  # Phase 6: trace metadata summary


@dataclass
class NarrativeRuntimeAgentInput:
    """Input contract for narrative runtime agent."""
    runtime_state: dict[str, Any]  # Current RuntimeState (committed scene, actor positions, etc.)
    npc_agency_plan: dict[str, Any]  # NPCAgencyPlan with remaining initiatives
    dramatic_signature: dict[str, Any]  # Dramatic signature from current turn
    narrative_threads: list[dict[str, Any]]  # Active narrative threads
    session_id: str
    turn_number: int
    trace_id: Optional[str] = None
    enable_langfuse_tracing: bool = False


@dataclass
class NarrativeRuntimeAgentConfig:
    """Configuration for narrative runtime agent behavior."""
    max_narrator_blocks: int = 10
    motivation_pressure_threshold: float = 0.3
    ruhepunkt_check_interval: int = 1  # Check after each narrator block
    enable_optional_silence_filling: bool = True
    streaming_timeout_seconds: int = 60


@dataclass
class NarrativeRuntimeAgentEvent:
    """Individual event streamed by the agent."""
    event_id: str
    event_kind: NarrativeEventKind
    timestamp: datetime
    sequence_number: int
    data: dict[str, Any]

    def to_json(self) -> str:
        """Serialize event to JSON."""
        return json.dumps({
            "event_id": self.event_id,
            "event_kind": self.event_kind.value,
            "timestamp": self.timestamp.isoformat(),
            "sequence_number": self.sequence_number,
            "data": self.data,
        })


class NarrativeRuntimeAgent:
    """
    Event-based narrator that streams blocks based on NPC motivation pressure.

    The agent:
    1. Analyzes remaining NPC initiatives and motivation pressure
    2. Generates narrator blocks (inner perception/orientation only)
    3. Streams events to client while input is queued
    4. Signals ruhepunkt when NPC initiatives exhausted
    5. Respects narrative validation rules (no force, no prediction, no hidden intent)
    6. Optionally emits Langfuse trace scaffolds (Phase 6)
    """

    def __init__(self, config: Optional[NarrativeRuntimeAgentConfig] = None):
        self.config = config or NarrativeRuntimeAgentConfig()
        self._event_sequence = 0
        self._trace_scaffold = {}  # Collect trace metadata when tracing disabled

    def stream_narrator_blocks(
        self,
        agent_input: NarrativeRuntimeAgentInput,
    ) -> Generator[NarrativeRuntimeAgentEvent, None, None]:
        """
        Stream narrator blocks based on NPC motivation pressure.

        Yields NarrativeRuntimeAgentEvent objects. Caller receives events in real-time
        and sends to client (via SSE or WebSocket). When ruhepunkt_reached event is
        yielded, input queue can be processed.

        When enable_langfuse_tracing=False (default), emits trace scaffold events
        showing what would be instrumented if Langfuse were enabled (Phase 6).

        Args:
            agent_input: NarrativeRuntimeAgentInput with runtime state, NPC plans, etc.

        Yields:
            NarrativeRuntimeAgentEvent for each narrator block or ruhepunkt signal
        """
        block_count = 0
        try:
            # Phase 6: Emit trace scaffold start (if tracing disabled)
            if not agent_input.enable_langfuse_tracing:
                yield self._emit_trace_scaffold_emitted_event(agent_input.session_id)

            # Analyze NPC motivation pressure and remaining initiatives
            motivation_analysis = self._analyze_motivation_pressure(agent_input)

            # Stream narrator blocks while initiatives pending
            # Lazy import to avoid circular dependency with backend modules
            try:
                from app.observability.langfuse_adapter import LangfuseAdapter
                adapter = LangfuseAdapter.get_instance()
            except ImportError:
                adapter = None

            while (
                block_count < self.config.max_narrator_blocks
                and motivation_analysis["remaining_initiatives"] > 0
            ):
                # Get parent span from context and create narrator block span
                narrator_span = None
                if adapter:
                    parent_span = adapter.get_active_span()
                    if parent_span:
                        logger.info(f"[NARRATOR] Creating narrator.narrate_block span (block #{block_count}) for session {agent_input.session_id}")
                        narrator_span = adapter.create_child_span(
                            name="narrator.narrate_block",
                            input={
                                "block_sequence": block_count,
                                "pressure_score": motivation_analysis.get("pressure_score"),
                                "remaining_initiatives": motivation_analysis.get("remaining_initiatives"),
                            },
                            metadata={
                                "block_sequence": block_count,
                                "turn_number": agent_input.turn_number,
                                "session_id": agent_input.session_id,
                            },
                        )
                        if narrator_span:
                            logger.info(f"[NARRATOR] narrator.narrate_block span created successfully")
                    else:
                        logger.warning(f"[NARRATOR] No active parent span - narrator blocks won't be traced")
                else:
                    logger.debug(f"[NARRATOR] Adapter not available - narrator blocks won't be traced")

                try:
                    narrator_block = self._generate_narrator_block(
                        agent_input=agent_input,
                        motivation_analysis=motivation_analysis,
                        block_sequence=block_count,
                    )

                    # Validate narrator voice (no force, prediction, hidden intent)
                    validation_error = self._validate_narrative_output(narrator_block, agent_input)
                    if validation_error:
                        if narrator_span:
                            narrator_span.update(
                                output={"status": "rejected", "error": validation_error},
                                metadata={"validation_failed": True}
                            )
                            narrator_span.end()
                        yield self._emit_error_event(
                            session_id=agent_input.session_id,
                            error_code="narrative_validation_failed",
                            error_message=validation_error,
                        )
                        return

                    # Update span with block metrics
                    if narrator_span:
                        logger.info(f"[NARRATOR] Updating narrator.narrate_block span with block_id={narrator_block.get('block_id')}")
                        narrator_span.update(
                            output={
                                "block_id": narrator_block.get("block_id"),
                                "atmospheric_tone": narrator_block.get("atmospheric_tone"),
                                "text_length": len(narrator_block.get("narrator_text", "")),
                            },
                            metadata={
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "model": "mock",
                                "cost_usd": 0.0,
                                "atmospheric_tone": narrator_block.get("atmospheric_tone"),
                                "narrative_threads_referenced": len(narrator_block.get("narrative_threads_referenced", [])),
                            },
                        )
                        logger.info(f"[NARRATOR] Ending narrator.narrate_block span")
                        narrator_span.end()
                        logger.info(f"[NARRATOR] narrator.narrate_block span ended")

                    # Phase 6: Record trace scaffold for this narrator block
                    if not agent_input.enable_langfuse_tracing:
                        self._record_trace_scaffold(
                            event_type="narrator_block_generation",
                            metadata={
                                "block_id": narrator_block.get("block_id"),
                                "atmospheric_tone": narrator_block.get("atmospheric_tone"),
                                "block_sequence": block_count,
                                "pressure_score": narrator_block.get("pressure_score"),
                            },
                        )

                    # Emit narrator block event
                    yield self._emit_narrator_event(narrator_block, block_sequence=block_count)
                    block_count += 1

                    # Check ruhepunkt after each block (optional: recalculate pressure)
                    if block_count % self.config.ruhepunkt_check_interval == 0:
                        motivation_analysis = self._analyze_motivation_pressure(agent_input)

                except Exception as e:
                    if narrator_span:
                        narrator_span.update(
                            output={"status": "error", "error": str(e)},
                            metadata={"error": True}
                        )
                        narrator_span.end()
                    raise

            # Signal ruhepunkt (rest point) - input can now be processed
            yield self._emit_ruhepunkt_event(
                session_id=agent_input.session_id,
                block_count=block_count,
                motivation_analysis=motivation_analysis,
            )

            # Phase 6: Emit trace scaffold summary (if tracing disabled)
            if not agent_input.enable_langfuse_tracing:
                yield self._emit_trace_scaffold_summary_event(
                    session_id=agent_input.session_id,
                    block_count=block_count,
                )

            # Emit streaming complete event
            yield self._emit_streaming_complete_event(agent_input.session_id, block_count)

        except Exception as exc:
            logger.error(
                f"NarrativeRuntimeAgent streaming failed: {exc}",
                extra={"session_id": agent_input.session_id, "trace_id": agent_input.trace_id},
                exc_info=True,
            )
            yield self._emit_error_event(
                session_id=agent_input.session_id,
                error_code="streaming_exception",
                error_message=str(exc),
            )

    def _analyze_motivation_pressure(
        self,
        agent_input: NarrativeRuntimeAgentInput,
    ) -> dict[str, Any]:
        """
        Analyze NPC motivation pressure and remaining initiatives.

        Returns analysis of:
        - remaining_initiatives: count of unresolved NPC initiatives
        - pressure_score: aggregate motivation pressure (0.0 to 1.0)
        - initiative_actors: list of NPCs with pending initiatives
        - motivation_summary: human-readable pressure summary
        """
        npc_plan = agent_input.npc_agency_plan
        if not isinstance(npc_plan, dict):
            npc_plan = {}

        initiatives = npc_plan.get("initiatives", [])
        if not isinstance(initiatives, list):
            initiatives = []

        # Count unresolved initiatives (filter for valid dicts)
        remaining = 0
        initiative_actors = set()
        all_actors = set()

        for initiative in initiatives:
            if not isinstance(initiative, dict):
                continue
            all_actors.add(initiative.get("actor_id", "unknown"))
            if not initiative.get("resolved"):
                remaining += 1
                initiative_actors.add(initiative.get("actor_id", "unknown"))

        # Calculate pressure score based on motivation intensity and count
        pressure = 0.0
        if remaining > 0:
            pressure = min(1.0, remaining * 0.1 + 0.3)  # Simple heuristic

        return {
            "remaining_initiatives": remaining,
            "pressure_score": pressure,
            "initiative_actors": list(initiative_actors),
            "motivation_summary": (
                f"{remaining} unresolved initiatives from {len(all_actors)}"
                if remaining > 0
                else "All NPC initiatives resolved"
            ),
        }

    def _generate_narrator_block(
        self,
        agent_input: NarrativeRuntimeAgentInput,
        motivation_analysis: dict[str, Any],
        block_sequence: int,
    ) -> dict[str, Any]:
        """
        Generate a narrator block based on current motivation pressure (Phase 2).

        Narrator blocks convey inner perception/orientation only:
        - Scene atmosphere and emotional tone (observable)
        - Player's subjective sense of tension/calm from NPC motivation
        - Narrative thread connections visible to player
        - NPC emotional states (observable from behavior, not hidden intent)

        Generation strategy:
        1. Analyze motivation pressure and NPC actors
        2. Generate observational language about scene atmosphere
        3. Reference visible dramatic context and narrative threads
        4. Validate output against narrator voice rules
        """
        block_id = str(uuid4())

        # Extract dramatic context
        dramatic_sig = agent_input.dramatic_signature or {}
        primary_tension = dramatic_sig.get("primary_tension", "unresolved")
        runtime_state = agent_input.runtime_state or {}
        npc_count = len(motivation_analysis.get("initiative_actors", []))

        # Build narrator text based on motivation pressure and dramatic context
        pressure_score = motivation_analysis.get("pressure_score", 0.5)
        atmospheric_tone = self._determine_atmospheric_tone(pressure_score, primary_tension)

        # Phase 2: Generate context-aware narrator text with observational language
        narrator_text = self._synthesize_narrator_text(
            pressure_analysis=motivation_analysis,
            dramatic_context=dramatic_sig,
            narrative_threads=agent_input.narrative_threads,
            atmospheric_tone=atmospheric_tone,
            block_sequence=block_sequence,
        )

        # Reference narrative threads visible to player
        threads_referenced = self._select_visible_threads(
            agent_input.narrative_threads,
            motivation_analysis.get("initiative_actors", []),
            max_threads=2,
        )

        return {
            "block_id": block_id,
            "sequence": block_sequence,
            "narrator_text": narrator_text,
            "narrative_threads_referenced": threads_referenced,
            "atmospheric_tone": atmospheric_tone,
            "pressure_score": pressure_score,
            "npc_actors_involved": motivation_analysis.get("initiative_actors", []),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _determine_atmospheric_tone(self, pressure_score: float, primary_tension: str) -> str:
        """Determine atmospheric tone based on pressure and dramatic context."""
        if pressure_score > 0.8:
            return "escalating_tension"
        elif pressure_score > 0.5:
            return "mounting_pressure"
        elif pressure_score > 0.3:
            return "simmering_conflict"
        else:
            return "cautious_calm"

    def _synthesize_narrator_text(
        self,
        pressure_analysis: dict[str, Any],
        dramatic_context: dict[str, Any],
        narrative_threads: list[dict[str, Any]] | None,
        atmospheric_tone: str,
        block_sequence: int,
    ) -> str:
        """
        Synthesize narrator text using observational language (Phase 2).

        Valid patterns (from ADR-MVP3-013):
        - "You notice the pause..."
        - "The tension in the room..."
        - Perception-based: "A weight settles..."
        - Observable behavior: "Alain's expression hardens..."
        """
        remaining_initiatives = pressure_analysis.get("remaining_initiatives", 0)
        primary_tension = dramatic_context.get("primary_tension", "unresolved")

        # Build observational sentences based on tone and context
        sentences = []

        # Atmospheric opening (observational, not forced)
        if atmospheric_tone == "escalating_tension":
            sentences.append("The atmosphere grows denser with each passing moment.")
        elif atmospheric_tone == "mounting_pressure":
            sentences.append("A quiet weight settles over the space between you.")
        elif atmospheric_tone == "simmering_conflict":
            sentences.append("Beneath the surface, something shifts and tightens.")
        else:
            sentences.append("There is a pause—a measured quality to the air.")

        # Narrative thread connection (if available)
        if narrative_threads and isinstance(narrative_threads, list) and len(narrative_threads) > 0:
            first_thread = narrative_threads[0]
            if isinstance(first_thread, dict):
                thread_name = first_thread.get("thread_id", "the unfolding dynamic")
                sentences.append(f"You perceive the depth of {thread_name} threading through the moment.")

        # Tension source (observational, not secret intent revelation)
        if remaining_initiatives > 0:
            sentences.append(
                f"There is movement in the undertone—others are gathering energy for what comes next."
            )

        return " ".join(sentences)

    def _select_visible_threads(
        self,
        narrative_threads: list[dict[str, Any]] | None,
        initiative_actors: list[str],
        max_threads: int = 2,
    ) -> list[dict[str, Any]]:
        """Select narrative threads that are visible to player (not hidden intent)."""
        if not narrative_threads or not isinstance(narrative_threads, list):
            return []

        visible = []
        for thread in narrative_threads[:max_threads]:
            if not isinstance(thread, dict):
                continue
            thread_copy = dict(thread)
            # Remove any hidden/internal fields
            thread_copy.pop("hidden_intent", None)
            thread_copy.pop("secret", None)
            visible.append(thread_copy)
        return visible

    def _validate_narrative_output(
        self,
        narrator_block: dict[str, Any],
        agent_input: NarrativeRuntimeAgentInput,
    ) -> Optional[str]:
        """
        Validate narrator block against narrative voice rules (Phase 2).

        Enforces ADR-MVP3-013 narrator voice contract using regex patterns.

        Three rejected modes:
        1. dialogue_summary: Recaps what characters said/discussed
        2. forced_player_state: Tells player how they feel/decide
        3. hidden_npc_intent: Reveals undisclosed motivations

        Returns error message if validation fails, None if valid.
        """
        text = narrator_block.get("narrator_text", "")

        # Check for dialogue summary (cannot recap what characters discussed)
        for pattern in _NARRATOR_DIALOGUE_SUMMARY_PATTERNS:
            if pattern.search(text):
                return (
                    "Narrative validation failed: "
                    "narrator cannot summarize or recap dialogue between characters "
                    f"(pattern: {pattern.pattern})"
                )

        # Check for forced player state (cannot tell player how they feel/decide)
        for pattern in _NARRATOR_FORCED_STATE_PATTERNS:
            if pattern.search(text):
                return (
                    "Narrative validation failed: "
                    "narrator cannot force player emotional or decision state "
                    f"(pattern: {pattern.pattern})"
                )

        # Check for hidden intent revelation (cannot reveal undisclosed NPC motivations)
        for pattern in _NARRATOR_HIDDEN_INTENT_PATTERNS:
            if pattern.search(text):
                return (
                    "Narrative validation failed: "
                    "narrator cannot reveal undisclosed NPC internal motivations "
                    f"(pattern: {pattern.pattern})"
                )

        return None

    def _record_trace_scaffold(self, event_type: str, metadata: dict[str, Any]) -> None:
        """
        Record trace scaffold entry (Phase 6).

        Collects metadata about what would be traced if Langfuse were enabled.
        Used when enable_langfuse_tracing=False to provide observability scaffolds.
        """
        if event_type not in self._trace_scaffold:
            self._trace_scaffold[event_type] = []

        self._trace_scaffold[event_type].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata,
            "trace_status": "scaffold_only",
        })

    def _emit_trace_scaffold_emitted_event(
        self,
        session_id: str,
    ) -> NarrativeRuntimeAgentEvent:
        """
        Emit trace scaffold emitted event at start of streaming (Phase 6).

        Signals to client that tracing is disabled and JSON scaffolds will be provided.
        """
        self._event_sequence += 1
        return NarrativeRuntimeAgentEvent(
            event_id=str(uuid4()),
            event_kind=NarrativeEventKind.TRACE_SCAFFOLD_EMITTED,
            timestamp=datetime.now(timezone.utc),
            sequence_number=self._event_sequence,
            data={
                "trace_status": "scaffolds_only",
                "reason": "enable_langfuse_tracing=False",
                "session_id": session_id,
            },
        )

    def _emit_trace_scaffold_summary_event(
        self,
        session_id: str,
        block_count: int,
    ) -> NarrativeRuntimeAgentEvent:
        """
        Emit trace scaffold summary event at end of streaming (Phase 6).

        Provides collected trace metadata that would have been used for live Langfuse spans.
        """
        self._event_sequence += 1
        total_scaffolds = sum(len(v) for v in self._trace_scaffold.values())

        return NarrativeRuntimeAgentEvent(
            event_id=str(uuid4()),
            event_kind=NarrativeEventKind.TRACE_SCAFFOLD_SUMMARY,
            timestamp=datetime.now(timezone.utc),
            sequence_number=self._event_sequence,
            data={
                "total_scaffolds": total_scaffolds,
                "scaffold_types": list(self._trace_scaffold.keys()),
                "trace_scaffold": self._trace_scaffold,
                "blocks_streamed": block_count,
                "session_id": session_id,
            },
        )

    def _emit_narrator_event(
        self,
        narrator_block: dict[str, Any],
        block_sequence: int,
    ) -> NarrativeRuntimeAgentEvent:
        """Emit a narrator block event."""
        self._event_sequence += 1
        return NarrativeRuntimeAgentEvent(
            event_id=str(uuid4()),
            event_kind=NarrativeEventKind.NARRATOR_BLOCK,
            timestamp=datetime.now(timezone.utc),
            sequence_number=self._event_sequence,
            data={
                "narrator_block": narrator_block,
                "block_sequence": block_sequence,
            },
        )

    def _emit_ruhepunkt_event(
        self,
        session_id: str,
        block_count: int,
        motivation_analysis: dict[str, Any],
    ) -> NarrativeRuntimeAgentEvent:
        """Emit ruhepunkt (rest point) signal - input can now be processed."""
        self._event_sequence += 1
        return NarrativeRuntimeAgentEvent(
            event_id=str(uuid4()),
            event_kind=NarrativeEventKind.RUHEPUNKT_REACHED,
            timestamp=datetime.now(timezone.utc),
            sequence_number=self._event_sequence,
            data={
                "ruhepunkt_reached": True,
                "block_count": block_count,
                "remaining_initiatives": motivation_analysis["remaining_initiatives"],
                "motivation_summary": motivation_analysis["motivation_summary"],
                "session_id": session_id,
            },
        )

    def _emit_streaming_complete_event(
        self,
        session_id: str,
        block_count: int,
    ) -> NarrativeRuntimeAgentEvent:
        """Emit streaming complete event."""
        self._event_sequence += 1
        return NarrativeRuntimeAgentEvent(
            event_id=str(uuid4()),
            event_kind=NarrativeEventKind.STREAMING_COMPLETE,
            timestamp=datetime.now(timezone.utc),
            sequence_number=self._event_sequence,
            data={
                "streaming_complete": True,
                "block_count": block_count,
                "session_id": session_id,
            },
        )

    def _emit_error_event(
        self,
        session_id: str,
        error_code: str,
        error_message: str,
    ) -> NarrativeRuntimeAgentEvent:
        """Emit error event."""
        self._event_sequence += 1
        return NarrativeRuntimeAgentEvent(
            event_id=str(uuid4()),
            event_kind=NarrativeEventKind.ERROR,
            timestamp=datetime.now(timezone.utc),
            sequence_number=self._event_sequence,
            data={
                "error_code": error_code,
                "error_message": error_message,
                "session_id": session_id,
            },
        )
