from .version import AI_STACK_MILESTONE, AI_STACK_SEMANTIC_VERSION, RUNTIME_TURN_GRAPH_VERSION

# True only when LangGraph + LangChain imports succeeded (see try/ blocks below).
# If False, use `pip install -e "./ai_stack[test]"` or `pip install -r ai_stack/requirements-test.txt`
# plus editable `story_runtime_core`, and ensure the repository root is on PYTHONPATH.
LANGGRAPH_RUNTIME_EXPORT_AVAILABLE: bool = False
from .capabilities import (
    CapabilityAccessDeniedError,
    CapabilityDefinition,
    CapabilityInvocationError,
    CapabilityKind,
    CapabilityRegistry,
    CapabilityValidationError,
    RETRIEVAL_TRACE_SCHEMA_VERSION,
    build_retrieval_trace,
    capability_catalog,
    create_default_capability_registry,
    evidence_lane_mix_from_sources,
)
from .research_contract import (
    CanonIssueType,
    ContradictionStatus,
    CopyrightPosture,
    ExplorationAbortReason,
    ExplorationBudget,
    ExplorationRelationType,
    ImprovementProposalType,
    Perspective,
    ResearchStatus,
)
__all__ = [
    "AI_STACK_MILESTONE",
    "AI_STACK_SEMANTIC_VERSION",
    "RUNTIME_TURN_GRAPH_VERSION",
    "CapabilityAccessDeniedError",
    "CapabilityDefinition",
    "CapabilityInvocationError",
    "CapabilityKind",
    "CapabilityRegistry",
    "CapabilityValidationError",
    "RETRIEVAL_TRACE_SCHEMA_VERSION",
    "build_retrieval_trace",
    "capability_catalog",
    "create_default_capability_registry",
    "evidence_lane_mix_from_sources",
    "CanonIssueType",
    "ContradictionStatus",
    "CopyrightPosture",
    "ExplorationAbortReason",
    "ExplorationBudget",
    "ExplorationRelationType",
    "ImprovementProposalType",
    "Perspective",
    "ResearchStatus",
]

# Optional heavy modules are imported defensively so lightweight metadata imports
# (for MCP M1 validation) do not fail in minimal environments.
try:
    from .rag import (
        ContentClass,
        ContextPack,
        ContextPackAssembler,
        ContextRetriever,
        InMemoryRetrievalCorpus,
        RagIngestionPipeline,
        RETRIEVAL_PIPELINE_VERSION,
        RETRIEVAL_POLICY_VERSION,
        SourceEvidenceLane,
        SourceGovernanceView,
        SourceVisibilityClass,
        governance_view_for_chunk,
        RetrievalDomain,
        RetrievalDomainError,
        RetrievalHit,
        RetrievalRequest,
        RetrievalResult,
        RetrievalStatus,
        build_runtime_retriever,
    )

    __all__.extend(
        [
            "ContentClass",
            "ContextPack",
            "ContextPackAssembler",
            "ContextRetriever",
            "InMemoryRetrievalCorpus",
            "RagIngestionPipeline",
            "RETRIEVAL_PIPELINE_VERSION",
            "RETRIEVAL_POLICY_VERSION",
            "SourceEvidenceLane",
            "SourceGovernanceView",
            "SourceVisibilityClass",
            "governance_view_for_chunk",
            "RetrievalDomain",
            "RetrievalDomainError",
            "RetrievalHit",
            "RetrievalRequest",
            "RetrievalResult",
            "RetrievalStatus",
            "build_runtime_retriever",
        ]
    )
except ModuleNotFoundError:
    pass

try:
    from .langgraph_runtime import (
        RuntimeTurnGraphExecutor,
        build_seed_improvement_graph,
        build_seed_writers_room_graph,
        ensure_langgraph_available,
    )

    LANGGRAPH_RUNTIME_EXPORT_AVAILABLE = True

    __all__.extend(
        [
            "RuntimeTurnGraphExecutor",
            "build_seed_improvement_graph",
            "build_seed_writers_room_graph",
            "ensure_langgraph_available",
        ]
    )
except ModuleNotFoundError:
    pass

__all__.append("LANGGRAPH_RUNTIME_EXPORT_AVAILABLE")

try:
    from .langchain_integration import (
        LangChainRetrieverBridge,
        RuntimeInvocationResult,
        RuntimeTurnStructuredOutput,
        WritersRoomInvocationResult,
        WritersRoomStructuredOutput,
        build_capability_tool_bridge,
        build_langchain_retriever_bridge,
        invoke_runtime_adapter_with_langchain,
        invoke_writers_room_adapter_with_langchain,
    )

    __all__.extend(
        [
            "LangChainRetrieverBridge",
            "RuntimeInvocationResult",
            "RuntimeTurnStructuredOutput",
            "WritersRoomInvocationResult",
            "WritersRoomStructuredOutput",
            "build_capability_tool_bridge",
            "build_langchain_retriever_bridge",
            "invoke_runtime_adapter_with_langchain",
            "invoke_writers_room_adapter_with_langchain",
        ]
    )
except ModuleNotFoundError:
    pass
