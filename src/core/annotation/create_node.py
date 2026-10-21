from dataclasses import replace

from core.annotation.entity.annotation import Annotation, get_matching_node


def create_node(annotation: Annotation, x: float) -> tuple[Annotation, int]:
    """Finds matching node within annotation or creates new one. Returns new annotation object
    with changes and node id."""
    nodes = annotation.nodes.copy()
    if len(nodes) == 0:
        new_node_idx = 0
    else:
        new_node_idx = max([node for node in nodes]) + 1

    node = get_matching_node(nodes, x)
    if node is None:
        nodes[new_node_idx] = x
        node = new_node_idx

    return replace(annotation, nodes=nodes), node
