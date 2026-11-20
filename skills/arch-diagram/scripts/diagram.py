#!/usr/bin/env python3
"""Render a grid-based architecture diagram.

Theme JSON keys: font (CSS font stack), grid, node_width, node_height and
radius (positive grid-aligned pixels); background, text, edge, node_fill and
node_text (CSS colours); domains maps domain names to {primary, light} colours.
Optional kind_fills maps node kinds to fill colours; show_kind adds the kind to
node sublabels. Domain primary colours outline nodes and groups, while light
colours fill groups. Theme files are independent and may define any domains.
"""

import argparse
import html
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

KINDS = {"component", "actor", "external", "data", "queue"}
THEMES = Path(__file__).resolve().parent.parent / "themes"


class DiagramError(ValueError):
    pass


def load_json(path):
    try:
        with open(path, encoding="utf-8") as source:
            return json.load(source)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DiagramError(f"{path}: {exc}") from exc


def load_theme(name):
    path = THEMES / (name + ".json") if name in {"ibm", "c4", "mono"} else Path(name)
    theme = load_json(path)
    if not isinstance(theme, dict):
        raise DiagramError("theme: expected an object")
    for field in ("font", "background", "text", "edge", "node_fill", "node_text"):
        if not isinstance(theme.get(field), str) or not theme[field]:
            raise DiagramError(f"theme.{field}: expected a nonempty string")
    for field in ("grid", "node_width", "node_height", "radius"):
        if type(theme.get(field)) is not int or theme[field] <= 0:
            raise DiagramError(f"theme.{field}: expected a positive integer")
    for field in ("node_width", "node_height", "radius"):
        if theme[field] % theme["grid"]:
            raise DiagramError(f"theme.{field}: must be a multiple of grid")
    domains = theme.get("domains")
    if not isinstance(domains, dict) or "default" not in domains:
        raise DiagramError("theme.domains: expected an object with a default domain")
    for name, domain in domains.items():
        if not isinstance(domain, dict) or any(
            not isinstance(domain.get(k), str) or not domain[k] for k in ("primary", "light")
        ):
            raise DiagramError(f"theme.domains.{name}: expected primary and light colours")
    if "kind_fills" in theme and (
        not isinstance(theme["kind_fills"], dict)
        or any(k not in KINDS or not isinstance(v, str) for k, v in theme["kind_fills"].items())
    ):
        raise DiagramError("theme.kind_fills: expected a mapping of kinds to colours")
    if "show_kind" in theme and type(theme["show_kind"]) is not bool:
        raise DiagramError("theme.show_kind: expected a boolean")
    return theme


def validate(spec, theme):
    if not isinstance(spec, dict):
        raise DiagramError("spec: expected an object")

    def string(obj, key, where, required=False):
        if key not in obj:
            if required:
                raise DiagramError(f"{where}.{key}: required")
        elif not isinstance(obj[key], str) or (required and not obj[key]):
            raise DiagramError(f"{where}.{key}: expected {'a nonempty' if required else 'a'} string")

    string(spec, "title", "spec", True)
    string(spec, "subtitle", "spec")
    string(spec, "theme", "spec", True) if "theme" in spec else None
    if "legend" in spec and type(spec["legend"]) is not bool:
        raise DiagramError("legend: expected a boolean")
    for key in ("nodes", "groups", "edges"):
        if key == "nodes" and key not in spec:
            raise DiagramError("nodes: required")
        if not isinstance(spec.get(key, []), list):
            raise DiagramError(f"{key}: expected an array")
    objects, nodes, groups, cells = {}, {}, {}, {}
    for key in ("nodes", "groups"):
        for index, obj in enumerate(spec.get(key, [])):
            where = f"{key}[{index}]"
            if not isinstance(obj, dict):
                raise DiagramError(f"{where}: expected an object")
            string(obj, "id", where, True)
            ident = obj["id"]
            if ident in objects:
                raise DiagramError(f"duplicate id: {ident}")
            string(obj, "label", ident, True)
            string(obj, "domain", ident)
            domain = obj.get("domain", "default")
            if domain not in theme["domains"]:
                raise DiagramError(f"{ident}.domain: unknown domain {domain!r}")
            objects[ident] = obj
            if key == "nodes":
                string(obj, "sublabel", ident)
                kind = obj.get("kind", "component")
                if not isinstance(kind, str) or kind not in KINDS:
                    raise DiagramError(f"{ident}.kind: invalid kind {kind!r}")
                for axis in ("col", "row"):
                    if type(obj.get(axis)) is not int or obj[axis] < 0:
                        raise DiagramError(f"{ident}.{axis}: expected a nonnegative integer")
                cell = (obj["col"], obj["row"])
                if cell in cells:
                    raise DiagramError(f"{ident}: overlapping grid cell with {cells[cell]}")
                cells[cell] = ident
                nodes[ident] = obj
            else:
                if not isinstance(obj.get("children"), list) or not obj["children"]:
                    raise DiagramError(f"{ident}.children: expected a nonempty array")
                groups[ident] = obj
    parents = {}
    for ident, group in groups.items():
        for child in group["children"]:
            if not isinstance(child, str) or child not in objects:
                raise DiagramError(f"{ident}.children: unknown id {child!r}")
            if child in parents:
                raise DiagramError(f"{child}: belongs to multiple groups ({parents[child]}, {ident})")
            parents[child] = ident
    visiting, visited = set(), set()

    def visit(ident):
        if ident in visiting:
            raise DiagramError(f"{ident}: group cycle")
        if ident in visited:
            return
        visiting.add(ident)
        for child in groups[ident]["children"]:
            if child in groups:
                visit(child)
        visiting.remove(ident)
        visited.add(ident)

    for ident in groups:
        visit(ident)
    for index, edge in enumerate(spec.get("edges", [])):
        if not isinstance(edge, dict):
            raise DiagramError(f"edges[{index}]: expected an object")
        for end in ("from", "to"):
            value = edge.get(end)
            if not isinstance(value, str) or value not in objects:
                raise DiagramError(f"edges[{index}].{end}: unknown id {value!r}")
        string(edge, "label", f"edges[{index}]")
        if edge.get("style", "solid") not in ("solid", "dashed"):
            raise DiagramError(f"edges[{index}].style: invalid style {edge['style']!r}")
    return nodes, groups, parents


def layout(spec, theme, nodes, groups, parents):
    grid = theme["grid"]

    def snap(n):
        return math.ceil(n / grid) * grid

    pad, band = snap(16), snap(24)
    depth = max((sum(1 for _ in ancestors(i, parents)) for i in nodes), default=0)
    margin = snap(32) + depth * (pad + band)
    hgap = snap(64) + 2 * depth * pad
    for edge in spec.get("edges", []):
        source, target = nodes.get(edge["from"]), nodes.get(edge["to"])
        if source and target and abs(source["col"] - target["col"]) == 1:
            label_width = 0.6 * 12 * len(edge.get("label", ""))
            hgap = max(hgap, snap(label_width + 32))
    vgap = snap(64) + 2 * depth * (pad + band)
    title_height = snap(72)
    w, h = theme["node_width"], theme["node_height"]
    boxes = {
        ident: (margin + node["col"] * (w + hgap), margin + title_height + node["row"] * (h + vgap), w, h)
        for ident, node in nodes.items()
    }
    order = []

    def group_box(ident):
        if ident in boxes:
            return boxes[ident]
        children = [group_box(child) for child in groups[ident]["children"]]
        left = min(b[0] for b in children) - pad
        top = min(b[1] for b in children) - pad - band
        right = max(b[0] + b[2] for b in children) + pad
        bottom = max(b[1] + b[3] for b in children) + pad
        boxes[ident] = left, top, right - left, bottom - top
        order.append(ident)
        return boxes[ident]

    for ident in groups:
        group_box(ident)
    domains = sorted({obj.get("domain", "default") for obj in list(nodes.values()) + list(groups.values())})
    styles = sorted({e.get("style", "solid") for e in spec.get("edges", [])})
    legend = spec.get("legend", True)
    legend_width = snap(max(208, max((len(d) for d in domains), default=0) * 9 + 64))
    legend_height = snap(40 + 24 * (len(domains) + len(styles))) if legend else 0
    content_right = max(
        [b[0] + b[2] for b in boxes.values()]
        + [snap(32 + 0.6 * 20 * len(spec["title"])), snap(32 + 0.6 * 12 * len(spec.get("subtitle", "")))]
    )
    content_bottom = max((b[1] + b[3] for b in boxes.values()), default=title_height)
    gap = snap(32)
    content_bottom = max(content_bottom, title_height)
    if legend:
        below_width = max(content_right, gap + legend_width) + gap
        below_height = content_bottom + gap + legend_height + gap
        right_width = content_right + gap + legend_width + gap
        right_height = max(content_bottom, title_height + legend_height) + gap
        if below_width * below_height <= right_width * right_height:
            width, height = below_width, below_height
            legend_box = (width - gap - legend_width, content_bottom + gap, legend_width, legend_height)
        else:
            width, height = right_width, right_height
            legend_box = (
                content_right + gap,
                max(title_height, content_bottom - legend_height),
                legend_width,
                legend_height,
            )
    else:
        width, height = content_right + gap, content_bottom + gap
        legend_box = (0, 0, 0, 0)
    return boxes, list(reversed(order)), domains, styles, (width, height), legend_box


def ancestors(ident, parents):
    while ident in parents:
        ident = parents[ident]
        yield ident


def route(source, target):
    x, y, w, h = source
    a, b, c, d = target
    if x != a:
        start = (x + w, y + h // 2) if x < a else (x, y + h // 2)
        end = (a, b + d // 2) if x < a else (a + c, b + d // 2)
        mid = (start[0] + end[0]) // 2
        return [start, (mid, start[1]), (mid, end[1]), end]
    start = (x + w // 2, y + h) if y <= b else (x + w // 2, y)
    end = (a + c // 2, b) if y <= b else (a + c // 2, b + d)
    mid = (start[1] + end[1]) // 2
    return [start, (start[0], mid), (end[0], mid), end]


def sublabel(node, theme):
    parts = []
    if theme.get("show_kind"):
        parts.append("[" + node.get("kind", "component") + "]")
    if node.get("sublabel"):
        parts.append(node["sublabel"])
    return " ".join(parts)


def render_svg(spec, theme, nodes, groups, layout_data):
    boxes, group_order, domains, styles, (width, height), legend = layout_data
    ns = "http://www.w3.org/2000/svg"
    ET.register_namespace("", ns)
    root = ET.Element(
        f"{{{ns}}}svg", {"viewBox": f"0 0 {width} {height}", "width": str(width), "height": str(height), "role": "img"}
    )

    def element(tag, attrs, parent=root, text=None):
        el = ET.SubElement(parent, f"{{{ns}}}{tag}", {k: str(v) for k, v in attrs.items()})
        if text is not None:
            el.text = text
        return el

    def rect(box, **attrs):
        x, y, w, h = box
        return element("rect", dict(x=x, y=y, width=w, height=h, **attrs))

    def text(x, y, value, size=14, **attrs):
        element(
            "text",
            {"x": x, "y": y, "fill": theme["text"], "font-family": theme["font"], "font-size": size, **attrs},
            text=value,
        )

    defs = element("defs", {})
    marker = element(
        "marker",
        {
            "id": "arrow",
            "viewBox": "0 0 10 10",
            "refX": 9,
            "refY": 5,
            "markerWidth": 8,
            "markerHeight": 8,
            "orient": "auto-start-reverse",
        },
        defs,
    )
    element("path", {"d": "M 0 0 L 10 5 L 0 10 z", "fill": theme["edge"]}, marker)
    rect((0, 0, width, height), fill=theme["background"])
    text(32, 32, spec["title"], 20, **{"font-weight": "600"})
    if spec.get("subtitle"):
        text(32, 56, spec["subtitle"], 12)
    for ident in group_order:
        group, box = groups[ident], boxes[ident]
        domain = theme["domains"][group.get("domain", "default")]
        rect(box, fill=domain["light"], stroke=domain["primary"], **{"stroke-width": 1})
        text(box[0] + 16, box[1] + 20, group["label"], 14, **{"font-weight": "600"})
    for edge in spec.get("edges", []):
        points = route(boxes[edge["from"]], boxes[edge["to"]])
        attrs = {
            "points": " ".join(f"{x},{y}" for x, y in points),
            "fill": "none",
            "stroke": theme["edge"],
            "stroke-width": 1,
            "marker-end": "url(#arrow)",
        }
        if edge.get("style") == "dashed":
            attrs["stroke-dasharray"] = "8 4"
        element("polyline", attrs)
    for ident, node in nodes.items():
        x, y, w, h = boxes[ident]
        kind = node.get("kind", "component")
        color = theme["domains"][node.get("domain", "default")]["primary"]
        fill = theme.get("kind_fills", {}).get(kind, theme["node_fill"])
        attrs = {"fill": fill, "stroke": color, "stroke-width": 1}
        if kind == "actor":
            element("ellipse", dict(cx=x + w // 2, cy=y + h // 2, rx=w // 2, ry=h // 2, **attrs))
        elif kind == "data":
            element(
                "path",
                dict(
                    d=(
                        f"M {x} {y + 8} C {x} {y - 3} {x + w} {y - 3} {x + w} {y + 8} L {x + w} {y + h - 8} "
                        f"C {x + w} {y + h + 3} {x} {y + h + 3} {x} {y + h - 8} Z "
                        f"M {x} {y + 8} C {x} {y + 19} {x + w} {y + 19} {x + w} {y + 8}"
                    ),
                    **attrs,
                ),
            )
        elif kind == "queue":
            element("polygon", dict(points=f"{x + 16},{y} {x + w},{y} {x + w - 16},{y + h} {x},{y + h}", **attrs))
        else:
            rect((x, y, w, h), rx=h // 2 if kind == "external" else theme["radius"], **attrs)
        sub = sublabel(node, theme)
        text(
            x + w // 2,
            y + h // 2 - (3 if sub else -5),
            node["label"],
            14,
            **{"font-weight": "600", "text-anchor": "middle", "fill": theme["node_text"]},
        )
        if sub:
            text(x + w // 2, y + h // 2 + 15, sub, 12, **{"text-anchor": "middle", "fill": theme["node_text"]})
    for edge in spec.get("edges", []):
        if not edge.get("label"):
            continue
        points = route(boxes[edge["from"]], boxes[edge["to"]])
        cx = (points[1][0] + points[2][0]) / 2
        cy = (points[1][1] + points[2][1]) / 2
        grid = theme["grid"]
        label_width = math.ceil((0.6 * 12 * len(edge["label"]) + 8) / grid) * grid
        label_height = math.ceil(20 / grid) * grid
        x = math.floor((cx - label_width / 2) / grid) * grid
        y = math.floor((cy - label_height / 2) / grid) * grid
        rect((x, y, label_width, label_height), fill=theme["background"], **{"class": "edge-label-background"})
        text(x + label_width / 2, y + (label_height - 12) / 2 + 10, edge["label"], 12, **{"text-anchor": "middle"})
    if spec.get("legend", True):
        x, y, w, h = legend
        rect(legend, fill=theme["background"], stroke=theme["edge"], **{"stroke-width": 1})
        text(x + 16, y + 20, "Legend", 14, **{"font-weight": "600"})
        for index, domain in enumerate(domains):
            yy = y + 32 + index * 24
            rect(
                (x + 16, yy, 16, 16), fill=theme["domains"][domain]["light"], stroke=theme["domains"][domain]["primary"]
            )
            text(x + 40, yy + 13, domain, 12)
        for index, style in enumerate(styles):
            yy = y + 32 + (len(domains) + index) * 24
            attrs = {"x1": x + 16, "x2": x + 32, "y1": yy + 8, "y2": yy + 8, "stroke": theme["edge"], "stroke-width": 1}
            if style == "dashed":
                attrs["stroke-dasharray"] = "8 4"
            element("line", attrs)
            text(x + 40, yy + 13, style, 12)
    return ET.ElementTree(root)


def render_drawio(spec, theme, nodes, groups, layout_data):
    boxes, group_order, domains, styles, (width, height), legend = layout_data
    root = ET.Element("mxfile", {"host": "app.diagrams.net"})
    diagram = ET.SubElement(root, "diagram", {"name": spec["title"]})
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        {
            "dx": str(width),
            "dy": str(height),
            "grid": "1",
            "gridSize": str(theme["grid"]),
            "page": "1",
            "pageWidth": str(width),
            "pageHeight": str(height),
            "background": theme["background"],
        },
    )
    cells = ET.SubElement(model, "root")
    ET.SubElement(cells, "mxCell", {"id": "0"})
    ET.SubElement(cells, "mxCell", {"id": "1", "parent": "0"})
    ids = {ident: f"object-{i}" for i, ident in enumerate(list(nodes) + list(groups))}
    font = theme["font"].split(",")[0].strip()

    def vertex(ident, value, box, style):
        cell = ET.SubElement(
            cells, "mxCell", {"id": ident, "value": value, "style": style, "vertex": "1", "parent": "1"}
        )
        geometry = dict(zip(("x", "y", "width", "height"), map(str, box), strict=True))
        ET.SubElement(cell, "mxGeometry", {**geometry, "as": "geometry"})

    base = f"html=1;whiteSpace=wrap;fontFamily={font};fontColor={theme['text']};"
    title = html.escape(spec["title"])
    if spec.get("subtitle"):
        title += '<br><span style="font-size:12px;font-weight:normal">' + html.escape(spec["subtitle"]) + "</span>"
    vertex(
        "title",
        title,
        (32, 8, max(192, width - 64), 64),
        base + "strokeColor=none;fillColor=none;align=left;verticalAlign=top;fontSize=20;fontStyle=1;",
    )
    for ident in group_order:
        group = groups[ident]
        domain = theme["domains"][group.get("domain", "default")]
        vertex(
            ids[ident],
            html.escape(group["label"]),
            boxes[ident],
            base
            + f"fillColor={domain['light']};strokeColor={domain['primary']};strokeWidth=1;align=left;"
            + "verticalAlign=top;spacingLeft=16;spacingTop=4;fontSize=14;fontStyle=1;",
        )
    for ident, node in nodes.items():
        kind = node.get("kind", "component")
        domain = theme["domains"][node.get("domain", "default")]
        fill = theme.get("kind_fills", {}).get(kind, theme["node_fill"])
        shape = {
            "component": "rounded=1;arcSize=12;",
            "actor": "ellipse;",
            "external": "rounded=1;arcSize=100;",
            "data": "shape=cylinder3;",
            "queue": "shape=parallelogram;",
        }[kind]
        label = '<span style="font-size:14px;font-weight:600">' + html.escape(node["label"]) + "</span>"
        sub = sublabel(node, theme)
        if sub:
            label += '<br><span style="font-size:12px;font-weight:normal">' + html.escape(sub) + "</span>"
        vertex(
            ids[ident],
            label,
            boxes[ident],
            base
            + shape
            + f"fillColor={fill};strokeColor={domain['primary']};fontColor={theme['node_text']};strokeWidth=1;",
        )
    for index, edge in enumerate(spec.get("edges", [])):
        style = (
            base
            + "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeWidth=1;"
            + f"strokeColor={theme['edge']};fontSize=12;labelBackgroundColor={theme['background']};"
        )
        if edge.get("style") == "dashed":
            style += "dashed=1;"
        cell = ET.SubElement(
            cells,
            "mxCell",
            {
                "id": f"edge-{index}",
                "value": html.escape(edge.get("label", "")),
                "style": style,
                "edge": "1",
                "parent": "1",
                "source": ids[edge["from"]],
                "target": ids[edge["to"]],
            },
        )
        geo = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        points = ET.SubElement(geo, "Array", {"as": "points"})
        for x, y in route(boxes[edge["from"]], boxes[edge["to"]])[1:3]:
            ET.SubElement(points, "mxPoint", {"x": str(x), "y": str(y)})
    if spec.get("legend", True):
        x, y, w, h = legend
        vertex(
            "legend",
            "Legend",
            legend,
            base
            + f"fillColor={theme['background']};strokeColor={theme['edge']};align=left;verticalAlign=top;"
            + "spacingLeft=16;spacingTop=4;fontStyle=1;fontSize=14;",
        )
        for i, domain in enumerate(domains):
            yy = y + 32 + i * 24
            colors = theme["domains"][domain]
            vertex(
                f"swatch-{i}",
                "",
                (x + 16, yy, 16, 16),
                base + f"fillColor={colors['light']};strokeColor={colors['primary']};",
            )
            vertex(
                f"domain-{i}",
                html.escape(domain),
                (x + 40, yy, w - 48, 16),
                base + "fillColor=none;strokeColor=none;align=left;fontSize=12;",
            )
        for i, style in enumerate(styles):
            yy = y + 32 + (len(domains) + i) * 24
            vertex(
                f"line-{i}",
                "",
                (x + 16, yy, 16, 16),
                base + f"shape=line;strokeColor={theme['edge']};" + ("dashed=1;" if style == "dashed" else ""),
            )
            vertex(
                f"style-{i}",
                style,
                (x + 40, yy, w - 48, 16),
                base + "fillColor=none;strokeColor=none;align=left;fontSize=12;",
            )
    return ET.ElementTree(root)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", help="JSON diagram specification")
    parser.add_argument("-o", "--output", help="output basename")
    parser.add_argument("--theme", help="ibm, c4, mono, or a theme JSON path")
    parser.add_argument("--format", choices=("drawio", "svg", "both"), default="both")
    parser.add_argument("--check", action="store_true", help="validate without writing output")
    args = parser.parse_args(argv)
    try:
        spec = load_json(args.spec)
        if not isinstance(spec, dict):
            raise DiagramError("spec: expected an object")
        theme_name = args.theme if args.theme is not None else spec.get("theme", "ibm")
        if not isinstance(theme_name, str) or not theme_name:
            raise DiagramError("theme: expected a nonempty string")
        theme = load_theme(theme_name)
        nodes, groups, parents = validate(spec, theme)
        if args.check:
            print("Spec is valid")
            return 0
        if not args.output:
            raise DiagramError("-o/--output is required unless --check is used")
        data = layout(spec, theme, nodes, groups, parents)
        for fmt in ("drawio", "svg") if args.format == "both" else (args.format,):
            tree = (render_drawio if fmt == "drawio" else render_svg)(spec, theme, nodes, groups, data)
            path = args.output + "." + fmt
            tree.write(path, encoding="utf-8", xml_declaration=True)
            print(path)
        return 0
    except (DiagramError, OSError, RecursionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
