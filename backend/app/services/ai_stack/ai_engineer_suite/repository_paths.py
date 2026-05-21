"""Repository and RAG artifact path resolution helpers."""

from __future__ import annotations

from .common import *

def _is_filesystem_root(p: Path) -> bool:
    """True if ``p`` is `/` (POSIX) or a drive root like ``C:\\`` (Windows)."""
    r = p.resolve()
    return r.parent == r


def _is_wos_repo_root(candidate: Path) -> bool:
    """True if ``candidate`` looks like the World of Shadows repo (``backend/app`` package)."""
    if not candidate.is_dir() or _is_filesystem_root(candidate):
        return False
    return (candidate / "backend" / "app").is_dir()


def _is_slim_backend_deploy_root(candidate: Path) -> bool:
    """True if ``candidate`` is a deploy tree with only ``app/`` (no monorepo ``backend/`` wrapper).

    Used for hosts that ship ``<deploy>/app/...`` without a top-level ``backend/`` directory.
    RAG persistence uses ``<deploy>/.wos/``; ingestion may see fewer sources than a full clone.
    """
    if not candidate.is_dir() or _is_filesystem_root(candidate):
        return False
    if (candidate / "backend" / "app").is_dir():
        return False
    app_pkg = candidate / "app"
    if not app_pkg.is_dir():
        return False
    return (app_pkg / "__init__.py").is_file() and (app_pkg / "services").is_dir()


def _is_acceptable_rag_root(candidate: Path) -> bool:
    return _is_wos_repo_root(candidate) or _is_slim_backend_deploy_root(candidate)


def _walk_best_rag_root(start: Path) -> Path | None:
    """Walk parents from ``start``; prefer full monorepo root, else slim ``<deploy>/app`` parent."""
    wos_hit: Path | None = None
    slim_hit: Path | None = None
    cur = start.resolve()
    for _ in range(22):
        if _is_filesystem_root(cur):
            break
        if _is_wos_repo_root(cur):
            wos_hit = cur
        if _is_slim_backend_deploy_root(cur):
            slim_hit = cur
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return wos_hit or slim_hit


def _repo_root() -> Path:
    """World of Shadows repository root for ``.wos/rag`` persistence.

    Naive ``Path(__file__).parents[3]`` becomes ``/`` on some host layouts, which then
    yields ``/.wos`` and *Permission denied*. Resolution order: validated ``WOS_REPO_ROOT``
    (env or ``current_app.config``), ``app.REPO_ROOT`` when it points at a usable tree,
    then upward walk from Flask ``root_path``, this file's directory, and ``cwd``.

    Accepts either a **full checkout** (directory containing ``backend/app/``) or a
    **slim deploy** root (directory containing ``app/`` with ``app/services/``).
    """
    candidates: list[str] = []
    for raw in (
        (os.environ.get("WOS_REPO_ROOT") or "").strip(),
    ):
        if raw:
            candidates.append(raw)
    try:
        cfg_val = current_app.config.get("WOS_REPO_ROOT")
        if isinstance(cfg_val, str) and cfg_val.strip() and cfg_val.strip() not in candidates:
            candidates.append(cfg_val.strip())
    except RuntimeError:
        pass
    for raw in candidates:
        p = Path(raw).expanduser().resolve()
        if _is_acceptable_rag_root(p):
            return p

    try:
        import app as app_module

        rr = getattr(app_module, "REPO_ROOT", None)
        if rr is not None:
            cand = Path(rr).resolve()
            if _is_acceptable_rag_root(cand):
                return cand
    except Exception:
        pass

    try:
        hit = _walk_best_rag_root(Path(current_app.root_path))
        if hit is not None:
            return hit
    except RuntimeError:
        pass

    hit = _walk_best_rag_root(Path(__file__).resolve().parent)
    if hit is not None:
        return hit

    hit = _walk_best_rag_root(Path.cwd())
    if hit is not None:
        return hit

    raise governance_error(
        "repo_root_unresolved",
        "Cannot resolve a writable RAG tree root. Set WOS_REPO_ROOT to either (1) the checkout that "
        "contains `backend/app/`, or (2) the deploy directory that contains `app/` (with `app/services/`). "
        "Alternatively run the API with its working directory inside such a tree, or set WOS_REPO_ROOT on the Flask config.",
        503,
        {"hint": "WOS_REPO_ROOT", "markers": ["backend/app", "app/services"]},
    )


def _remove_if_exists(path: Path) -> bool:
    if not path.exists():
        return False
    path.unlink()
    return True


def _build_rag_stack(*, force_corpus_rebuild: bool = False, force_dense_rebuild: bool = False, reset_cache: bool = False):
    global _RAG_STACK_CACHE
    root = _repo_root()
    corpus_path = root / _RUNTIME_CORPUS_REL
    npz_path = root / _EMBED_NPZ_REL
    meta_path = root / _EMBED_META_REL
    with _RAG_STACK_LOCK:
        if force_corpus_rebuild:
            _remove_if_exists(corpus_path)
        if force_dense_rebuild:
            _remove_if_exists(npz_path)
            _remove_if_exists(meta_path)
        if reset_cache:
            _RAG_STACK_CACHE = None
        if _RAG_STACK_CACHE is not None:
            cached_root, retriever, assembler, corpus = _RAG_STACK_CACHE
            if cached_root == root and not force_corpus_rebuild and not force_dense_rebuild:
                return retriever, assembler, corpus
        retriever, assembler, corpus = build_runtime_retriever(root)
        _RAG_STACK_CACHE = (root, retriever, assembler, corpus)
        return retriever, assembler, corpus



__all__ = (
    '_is_filesystem_root',
    '_is_wos_repo_root',
    '_is_slim_backend_deploy_root',
    '_is_acceptable_rag_root',
    '_walk_best_rag_root',
    '_repo_root',
    '_remove_if_exists',
    '_build_rag_stack',
)
