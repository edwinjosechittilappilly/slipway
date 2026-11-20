---
name: arch-diagram
description: Generate architecture diagrams as an editable draw.io file plus SVG in IBM Design Language, C4, or an organisation's brand style, from a small JSON spec on a grid. Use for system context, container, deployment or data-flow diagrams in design docs, one-pagers, ADRs and READMEs, or when asked for an architecture diagram, IBM-style diagram or C4 diagram.
---

# Architecture diagrams

Diagrams are code: a JSON spec you commit, rendered by `scripts/diagram.py` (Python 3, standard library only) into
`.drawio` (editable) and `.svg` (embeddable). Same spec, any theme.

## Process

1. **Pick one view.** C4 level 1 (context: people and systems), level 2 (containers: apps, stores, queues), or a
   deployment view (zones and networks as groups). At most 12 nodes; split bigger pictures into several views.
2. **Lay it out on a grid.** `col` follows the flow left to right: people in column 0, external systems in the last
   column. `row` separates parallel lanes. Put things that talk to each other in adjacent columns.
3. **Write the spec** to `docs/diagrams/<name>.json` (schema below; example in `examples/three-tier.json`).
4. **Render** (run from the repo root; `<skill>` is this skill's directory):

   ```bash
   python3 <skill>/scripts/diagram.py docs/diagrams/<name>.json -o docs/diagrams/<name> --theme ibm
   ```

   Themes: `ibm` (default), `c4`, `mono`, or a path to a brand theme JSON. `--format drawio|svg|both`.
   `--check` validates the spec without writing files.
5. **Look at the SVG** (open it, or read it as an image if your harness can). Fix crossings by swapping columns,
   not by adding nodes. Every colour must appear in the legend; colour is never the only signal.
6. **Commit** the `.json`, `.drawio` and `.svg` together and embed the SVG: `![Context](../diagrams/<name>.svg)`.
7. **Export** PNG or PDF only when asked, with draw.io desktop: `drawio -x -f png -o <name>.png <name>.drawio`
   (macOS binary: `/Applications/draw.io.app/Contents/MacOS/draw.io`). For freehand edits to an existing
   diagram, use the `drawio-skill`.

## Spec

```json
{
  "title": "Orders platform",
  "subtitle": "C4 level 2: containers",
  "theme": "ibm",
  "nodes": [
    {"id": "shopper", "label": "Shopper", "kind": "actor", "domain": "user", "col": 0, "row": 0},
    {"id": "web", "label": "Storefront", "sublabel": "React SPA", "domain": "compute", "col": 1, "row": 0},
    {"id": "api", "label": "Orders API", "sublabel": "FastAPI", "domain": "compute", "col": 2, "row": 0},
    {"id": "db", "label": "Orders DB", "sublabel": "PostgreSQL", "kind": "data", "domain": "data", "col": 3, "row": 0},
    {"id": "pay", "label": "Payment provider", "kind": "external", "domain": "external", "col": 3, "row": 1}
  ],
  "groups": [{"id": "vpc", "label": "Production VPC", "domain": "network", "children": ["web", "api", "db"]}],
  "edges": [
    {"from": "shopper", "to": "web", "label": "HTTPS"},
    {"from": "api", "to": "db", "label": "SQL"},
    {"from": "api", "to": "pay", "label": "Charges", "style": "dashed"}
  ]
}
```

- `kind`: `component` (default, rounded box), `actor` (ellipse), `external` (pill), `data` (cylinder), `queue`.
- `domain`: a key of the theme's `domains` (IBM: `compute`, `data`, `network`, `security`, `management`, `ai`,
  `user`, `external`, `default`). It sets the outline colour and the legend entry.
- `groups` nest (a group's `children` may be groups). A node belongs to at most one group.
- `edges[].style`: `solid` (default) or `dashed` (async, optional or external calls).
- Validation rejects unknown ids, duplicates, two nodes in one grid cell, and group cycles, naming the bad id.

## IBM Design Language rules the `ibm` theme applies

From IBM's technical diagram guidance: 8 px grid for every position and size; IBM Plex Sans (primary label 14 px
semibold, secondary 12 px); 1 px outlines; monochrome white nodes outlined in the domain's primary colour; groups
filled with the domain's 10-grade tint; near-black text; orthogonal grey connectors with arrowheads; a legend on
every diagram. Keep flows left to right, labels in sentence case, and no all-caps.

## Your organisation's style

Copy `themes/ibm.json` to `docs/diagrams/theme.json`, change `font`, colours and `domains` (any names you like), and
render with `--theme docs/diagrams/theme.json`. Theme keys are documented at the top of `scripts/diagram.py`.
