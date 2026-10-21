from dataclasses import replace

from core.annotation.entity.annotation import Annotation


def delete_annotation_interval(
    annotation: Annotation, type_idx: list[int], s_node: int, e_node: int
) -> Annotation:
    nodes = annotation.nodes

    types = []
    for idx, type in enumerate(annotation.types):
        if not idx in type_idx:
            types.append(type)
            continue

        labels = []
        for label in type.labels:
            if (
                nodes[label.e_node] < nodes[s_node]
                or nodes[label.s_node] > nodes[e_node]
            ):
                labels.append(label)
            else:
                text = label.label
                if nodes[label.s_node] < nodes[s_node]:
                    labels.append(replace(label, e_node=s_node, label=text))
                    text = ""
                if nodes[label.e_node] > nodes[e_node]:
                    labels.append(replace(label, s_node=e_node, label=text))

        types.append(replace(type, labels=labels))

    return replace(annotation, types=types)
