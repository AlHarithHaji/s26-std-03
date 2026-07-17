"""
linearizer.py — turn a normalized graph into an ordered list of Steps.

RESPONSIBILITY: walk the disassembly graph from its root and produce the flat,
ordered `Guide.steps`, applying the depth cut chosen by the user (FR 3.0). This
is the half of the load phase that encodes the disassembly grammar; validation
(validation.py) is the other half. The two are separate because they answer
different questions: validation asks "is this graph well-formed?", linearization
asks "in what order does one take it apart?".

THE GRAMMAR THIS ENCODES (confirmed empirically on Bialetti / Maria / Epson):
  - A diamond is a MACRO operation. Its ACTION children form a linear CHAIN
    (action_1 -> action_2 -> ...) describing HOW to perform it; the chain never
    branches and never mixes with components, so its order is purely topological.
  - A diamond's COMPONENT children are the RESULTS. At most ONE of them
    "continues" (leads onward to a further diamond); the rest are leaf outputs.
    Components are siblings with no topological order among them, so they are
    ordered by canvas geometry (x, then y) — the only ordering signal available.
  - Every diamond is reachable from the single root by following continuations.

TRAVERSAL ORDER: depth-first (DFS), one branch fully before the next. A
disassembly guide is executed one sub-system at a time, so DFS reads naturally;
breadth-first would interleave unrelated sub-systems step by step. (The URS says
"BFS with limited depth"; that phrase concerns the depth-CUT concept — stopping
at a level — not the order in which finished steps are listed. Depth is the
number of nested operations from the root, which we track with a counter
regardless of visitation order; we list steps branch-by-branch for readability.)

IMPLEMENTATION: an explicit stack, not recursion. This matches the cycle
detector in validation.py (one traversal technique across the package) and
cannot hit Python's recursion limit on a very deep model — the "survives the
course / reused by a later group" requirement makes deep inputs a real future
case, not a hypothetical. The cost is small and well-understood for a DFS.

NON-BLOCKING: like validation, linearization never raises on a malformed graph.
A cycle is broken by a visited-set; a missing piece yields a best-effort step.
The user may always proceed (FR 2.3).
"""

from __future__ import annotations

from .models import (
    Action,
    Component,
    DepthMode,
    DepthSpec,
    DisassemblyGraph,
    GraphNode,
    NodeType,
    Step,
    TraversalMode,
)


def linearize(
    graph: DisassemblyGraph,
    depth: DepthSpec,
    traversal: TraversalMode = TraversalMode.STRICT,
) -> tuple[Step, ...]:
    """
    Produce the ordered tuple of Steps for the given graph and depth choice.

    `traversal` controls how a grammar-violating graph is handled (orthogonal to
    depth): STRICT (default) follows only the grammatical continuation chain;
    LENIENT (not yet implemented) would maximize coverage on malformed graphs.

    Returns an empty tuple for an empty graph (validation reports that
    separately). Never raises on a malformed-but-parsable graph in STRICT mode;
    never mutates the graph.
    """
    if traversal is TraversalMode.LENIENT:
        raise NotImplementedError(
            "LENIENT traversal is reserved for a future need and not yet "
            "implemented. Use TraversalMode.STRICT (the default), which follows "
            "the grammatical continuation chain. LENIENT would visit all reachable "
            "diamonds including non-grammatical parallel branches; it was left "
            "unimplemented deliberately to avoid an untested second traversal "
            "until a real use case requires it."
        )

    root = find_root(graph)
    if root is None:
        return ()

    steps: list[Step] = []
    visited: set[int] = set()  # diamond ids already turned into a step (anti-cycle)

    # The traversal stack holds (diamond_id, depth) pairs. We seed it with the
    # diamonds directly reachable from the root, in REVERSE order: the stack is
    # LIFO, so pushing the first-by-geometry diamond LAST makes it pop FIRST,
    # giving left-to-right DFS order. This reversed() is the classic
    # stack-for-DFS subtlety — without it the branches come out mirrored.
    start_diamonds = _ordered_next_diamonds(graph, root)
    stack: list[tuple[int, int]] = [(d, 0) for d in reversed(start_diamonds)]

    while stack:
        diamond_id, depth_level = stack.pop()
        if diamond_id in visited:
            continue  # cycle or shared sub-graph: break here, do not loop
        visited.add(diamond_id)

        step, continuations = _build_step(
            graph, diamond_id, index=len(steps) + 1, depth=depth, depth_level=depth_level
        )
        steps.append(step)

        # Push the children we will descend into. `continuations` lists the
        # (next_diamond_id) we did NOT cut; pushed reversed for DFS order.
        for next_diamond in reversed(continuations):
            stack.append((next_diamond, depth_level + 1))

    return tuple(steps)


# =============================================================================
# STEP CONSTRUCTION
# =============================================================================

def _build_step(
    graph: DisassemblyGraph,
    diamond_id: int,
    index: int,
    depth: DepthSpec,
    depth_level: int,
) -> tuple[Step, list[int]]:
    """
    Build one Step from a diamond, and return (step, next_diamond_ids_to_descend).

    Separates the diamond's children by ROLE (by NodeType, never by array
    position): the action child opens the instruction chain; the component
    children are the results. Among the components, the one that continues is
    found by TOPOLOGY (it leads onward to a diamond); the rest are leaves.

    GRAMMAR (supervisor-confirmed): a composite continues into EXACTLY ONE
    operation — disassembly is a linear chain ("extract one, the rest
    continues"), not a tree. So at most one component continues, and that
    component leads to exactly one onward diamond. A component feeding several
    diamonds is an anomaly (reported by rule_composite_single_continuation); here
    we proceed best-effort by following ONE continuation (the first by geometry)
    and ignoring the rest — following them all would encode the wrong grammar.

    Depth cut: for the continuing component, ask should_stop(). If we stop, the
    component is emitted as a kept-whole leaf output (with its hidden-leaf count)
    and we do NOT descend.
    """
    diamond = graph.nodes[diamond_id]

    # --- the action chain (linear, topological order) ----------------------
    actions = _collect_action_chain(graph, diamond_id)

    # --- the component children, ordered by geometry ------------------------
    component_children = [
        k for k in graph.out_adj.get(diamond_id, ())
        if k in graph.nodes and graph.nodes[k].type is NodeType.COMPONENT
    ]
    component_children = _order_by_geometry(graph, component_children)

    outputs: list[Component] = []
    continues_as: Component | None = None
    next_diamonds_to_descend: list[int] = []

    for comp_id in component_children:
        onward_diamond = _continuation_diamond(graph, comp_id)

        if onward_diamond is None:
            # natural leaf: a final extracted part
            outputs.append(_to_component(graph.nodes[comp_id]))
            continue

        # This component continues the disassembly. Per the supervisor-confirmed
        # grammar, a single DIAMOND may produce SEVERAL continuing composites,
        # each disassembled along its own branch (the structure is a tree that
        # branches on a diamond's OUTPUTS — not a composite feeding two diamonds,
        # which remains forbidden and is flagged by validation). So we descend
        # into EVERY continuing output, not just the first. The traversal is DFS
        # (one branch fully before the next), so the flat step list stays
        # readable; the IR shape is unchanged.
        if should_stop(depth, graph.nodes[comp_id], depth_level + 1):
            # depth cut: keep this sub-assembly whole, count what is hidden inside
            leaf_count = _count_hidden_leaves(graph, comp_id)
            outputs.append(_to_component(
                graph.nodes[comp_id], kept_whole=True, contained_leaf_count=leaf_count
            ))
        else:
            comp = _to_component(graph.nodes[comp_id])
            # continues_as records the first continuing composite as the step's
            # primary continuation (reading reference); all continuing composites
            # are descended into below.
            if continues_as is None:
                continues_as = comp
            next_diamonds_to_descend.append(onward_diamond)

    step = Step(
        index=index,
        operation=diamond.text,
        actions=tuple(actions),
        outputs=tuple(outputs),
        continues_as=continues_as,
        tools_required=_collect_tools(actions),
    )
    return step, next_diamonds_to_descend


# =============================================================================
# DEPTH CUT PREDICATE
# =============================================================================

def should_stop(depth: DepthSpec, node: GraphNode, depth_level: int) -> bool:
    """
    Decide whether to STOP descending at a continuing component (keep it whole).

    One predicate, parametric on DepthSpec — the traversal is identical for all
    modes; only this answer changes. Adding a future depth mode means adding a
    branch here, not rewriting the traversal.

      FULL      : never stop (no limit at all — not "a large limit"; we do not
                  even look at depth_level).
      KEEP_MAIN : stop once we are past the first level of operations
                  (depth_level >= 1) — keep main assemblies whole.
      MANUAL    : stop at the specific nodes the user designated.
    """
    if depth.mode is DepthMode.FULL:
        return False
    if depth.mode is DepthMode.KEEP_MAIN:
        return depth_level >= 1
    if depth.mode is DepthMode.MANUAL:
        return node.id in depth.keep_whole_ids
    return False  # unknown mode: safest is to not cut


# =============================================================================
# GRAPH-WALKING HELPERS  (small, pure, individually testable)
# =============================================================================

def find_root(graph: DisassemblyGraph) -> int | None:
    """The node where disassembly starts: no incoming edge AND at least one
    outgoing edge. None if the graph has no such node.

    Public because more than one stage needs the root (linearization and the
    builder's product extraction). A fully isolated node is not a root (it starts
    nothing). If several nodes qualify (multiple roots — a validation warning), we
    pick the first deterministically so linearization still produces a guide
    (FR 2.3)."""
    roots = [
        nid for nid in graph.nodes
        if not graph.inc_adj.get(nid) and graph.out_adj.get(nid)
    ]
    if not roots:
        return None
    return sorted(roots)[0]


def _ordered_next_diamonds(graph: DisassemblyGraph, node_id: int) -> list[int]:
    """Diamonds directly reachable from a node, ordered by geometry."""
    diamonds = [
        k for k in graph.out_adj.get(node_id, ())
        if k in graph.nodes and graph.nodes[k].type is NodeType.DIAMOND
    ]
    return _order_by_geometry(graph, diamonds)


def _continuation_diamond(graph: DisassemblyGraph, component_id: int) -> int | None:
    """The diamond a component leads onward to, or None if it is a leaf.

    By the grammar a continuing component has exactly one onward diamond; if a
    malformed graph gives several, we take the first by geometry so we still
    descend somewhere (best-effort)."""
    onward = [
        k for k in graph.out_adj.get(component_id, ())
        if k in graph.nodes and graph.nodes[k].type is NodeType.DIAMOND
    ]
    if not onward:
        return None
    return _order_by_geometry(graph, onward)[0]


def _collect_action_chain(graph: DisassemblyGraph, diamond_id: int) -> list[Action]:
    """
    Collect every action node belonging to a diamond's operation, in order.

    A diamond's instructions may be modelled two ways (both valid — they only
    differ topologically):
      - CHAINED: one action child, then action -> action -> ... in sequence
        (Bialetti / Maria / Epson). Order is topological.
      - FAN-OUT: several action children hanging directly off the diamond, not
        linked to each other (Oranfresh). Siblings have no topological order, so
        they are ordered by geometry (x, then y) — exactly as component fan-outs
        are (nespresso). A mix of the two is handled too.

    Algorithm: do a small traversal from the diamond following ONLY action edges,
    collecting every action reachable. Within the traversal, siblings are visited
    in geometry order, so both a chain and a fan-out come out in a sensible
    reading order. A `seen` set guards against a malformed cyclic action graph.

    This replaces the earlier chain-only logic, which silently collected just the
    first action when the others were fan-out children — losing most of the
    instructions with no warning (observed on Oranfresh: 7 instructions, 1 kept).
    """
    # All action children directly under the diamond, in geometry order.
    heads = _order_by_geometry(graph, [
        k for k in graph.out_adj.get(diamond_id, ())
        if k in graph.nodes and graph.nodes[k].type is NodeType.ACTION
    ])
    if not heads:
        return []

    actions: list[Action] = []
    seen: set[int] = set()
    # Stack-based DFS over action edges. Push heads reversed so the first by
    # geometry is processed first (LIFO), keeping reading order.
    stack: list[int] = list(reversed(heads))
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        actions.append(_to_action(graph.nodes[current]))
        # follow any action successors of this action (the chained case), in
        # geometry order
        successors = _order_by_geometry(graph, [
            k for k in graph.out_adj.get(current, ())
            if k in graph.nodes and graph.nodes[k].type is NodeType.ACTION
        ])
        for nxt in reversed(successors):
            if nxt not in seen:
                stack.append(nxt)
    return actions


def _count_hidden_leaves(graph: DisassemblyGraph, component_id: int) -> int:
    """
    Count the leaf components hidden under a kept-whole sub-assembly.

    Explores the sub-graph below `component_id` (following all edges) and counts
    component nodes that are themselves leaves (no further component output). A
    visited-set guards against cycles. This is what tells the user how many real
    parts are inside a block they chose not to open.
    """
    leaves = 0
    seen: set[int] = set()
    stack = [component_id]
    while stack:
        nid = stack.pop()
        if nid in seen or nid not in graph.nodes:
            continue
        seen.add(nid)
        children = [k for k in graph.out_adj.get(nid, ()) if k in graph.nodes]
        # a component with no onward component/diamond is a physical leaf
        has_onward = any(
            graph.nodes[k].type in (NodeType.COMPONENT, NodeType.DIAMOND)
            for k in children
        )
        if graph.nodes[nid].type is NodeType.COMPONENT and not has_onward \
                and nid != component_id:
            leaves += 1
        stack.extend(children)
    return leaves


def _order_by_geometry(graph: DisassemblyGraph, node_ids: list[int]) -> list[int]:
    """
    Order sibling node ids by canvas position: left-to-right (x), then top-to-
    bottom (y). This is the only ordering signal for component fan-outs, whose
    siblings have no topological order (confirmed on nespresso, where edge
    arrival order is meaningless and x gives the natural reading order). Nodes
    with missing coordinates sort first (treated as 0) deterministically.
    """
    def key(nid: int) -> tuple[float, float]:
        node = graph.nodes[nid]
        return (node.x if node.x is not None else 0.0,
                node.y if node.y is not None else 0.0)
    return sorted(node_ids, key=key)


# =============================================================================
# GraphNode -> IR translation
# =============================================================================

def _to_component(
    node: GraphNode,
    kept_whole: bool = False,
    contained_leaf_count: int | None = None,
) -> Component:
    """Translate a graph component node into an IR Component (parse weight here)."""
    return Component(
        node_id=node.id,
        name=node.text,
        weight=_parse_weight(node.weight),
        weight_unit=node.weight_unit,
        material=node.material,
        color=node.color,
        image_path=node.image_path,
        kept_whole=kept_whole,
        contained_leaf_count=contained_leaf_count,
    )


def _to_action(node: GraphNode) -> Action:
    """Translate a graph action node into an IR Action."""
    return Action(
        node_id=node.id,
        text=node.text,
        tools=node.extra.get("tools") or None,
        image_path=node.image_path,
    )


def _parse_weight(weight: str | None) -> float | None:
    """Parse the raw weight string into a float; None/blank/garbage -> None."""
    if weight is None:
        return None
    try:
        return float(weight)
    except (TypeError, ValueError):
        return None


def _collect_tools(actions: list[Action]) -> tuple[str, ...]:
    """Deduplicated union of tools across a step's actions, order-preserving."""
    seen: list[str] = []
    for action in actions:
        if action.tools and action.tools not in seen:
            seen.append(action.tools)
    return tuple(seen)