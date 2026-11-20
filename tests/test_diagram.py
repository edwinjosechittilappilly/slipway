import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/arch-diagram/scripts/diagram.py"
EXAMPLE = ROOT / "skills/arch-diagram/examples/three-tier.json"
MODULE_SPEC = importlib.util.spec_from_file_location("diagram", SCRIPT)
diagram = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(diagram)
SVG = "{http://www.w3.org/2000/svg}"


class DiagramTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def run_spec(self, spec=None, *args):
        path = self.path / "spec.json"
        path.write_text(json.dumps(self.spec if spec is None else spec), encoding="utf-8")
        out = self.path / "diagram"
        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            status = diagram.main([str(path), "-o", str(out), *args])
        return status, stderr.getvalue(), out

    def test_example_outputs_parse_and_are_grid_aligned(self):
        status, error, out = self.run_spec()
        self.assertEqual(status, 0, error)
        drawio = ET.parse(str(out) + ".drawio")
        svg = ET.parse(str(out) + ".svg")
        self.assertEqual(drawio.getroot().tag, "mxfile")
        self.assertTrue(svg.getroot().get("viewBox"))
        for geo in drawio.findall(".//mxCell[@vertex='1']/mxGeometry"):
            for key in ("x", "y", "width", "height"):
                self.assertEqual(int(geo.get(key)) % 8, 0, (key, geo.attrib))
        for rect in svg.findall(".//" + SVG + "rect"):
            for key in ("x", "y", "width", "height"):
                self.assertEqual(int(rect.get(key)) % 8, 0, (key, rect.attrib))
        domains = {item.get("domain", "default") for item in self.spec["nodes"] + self.spec["groups"]}
        cells = drawio.findall(".//mxCell")
        actual = {c.get("value") for c in cells if c.get("id", "").startswith("domain-")}
        self.assertEqual(actual, domains)
        svg_text = [e.text for e in svg.findall(".//" + SVG + "text")]
        for domain in domains:
            self.assertIn(domain, svg_text)

    def test_edge_labels_do_not_overlap_nodes_and_legend_is_compact(self):
        status, error, out = self.run_spec()
        self.assertEqual(status, 0, error)
        svg = ET.parse(str(out) + ".svg").getroot()
        drawio = ET.parse(str(out) + ".drawio")
        labels = svg.findall(".//" + SVG + "rect[@class='edge-label-background']")
        self.assertEqual(len(labels), 2)

        def box(element):
            return tuple(int(element.get(key)) for key in ("x", "y", "width", "height"))

        def overlaps(a, b):
            return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]

        node_boxes = [
            box(drawio.find(f".//mxCell[@id='object-{index}']/mxGeometry")) for index in range(len(self.spec["nodes"]))
        ]
        for label in labels:
            for node in node_boxes:
                self.assertFalse(overlaps(box(label), node), (label.attrib, node))
        edges = drawio.findall(".//mxCell[@edge='1']")
        self.assertTrue(all("labelBackgroundColor=#ffffff;" in edge.get("style") for edge in edges))
        legend = box(drawio.find(".//mxCell[@id='legend']/mxGeometry"))
        groups = [
            box(drawio.find(f".//mxCell[@id='object-{index}']/mxGeometry"))
            for index in range(len(self.spec["nodes"]), len(self.spec["nodes"]) + len(self.spec["groups"]))
        ]
        content = node_boxes + groups
        right = max(b[0] + b[2] for b in content)
        bottom = max(b[1] + b[3] for b in content)
        self.assertTrue(legend[0] == right + 32 or legend[1] == bottom + 32)
        _, _, width, height = map(int, svg.get("viewBox").split())
        self.assertEqual(width, max(right, legend[0] + legend[2]) + 32)
        self.assertEqual(height, max(bottom, legend[1] + legend[3]) + 32)

    def test_long_adjacent_edge_label_expands_gap(self):
        self.spec["edges"][1]["label"] = "A long descriptive label " * 4
        status, error, out = self.run_spec()
        self.assertEqual(status, 0, error)
        drawio = ET.parse(str(out) + ".drawio")
        web = drawio.find(".//mxCell[@id='object-1']/mxGeometry")
        api = drawio.find(".//mxCell[@id='object-2']/mxGeometry")
        gap = int(api.get("x")) - int(web.get("x")) - int(web.get("width"))
        self.assertGreaterEqual(gap, 0.6 * 12 * len(self.spec["edges"][1]["label"]) + 32)

    def test_invalid_specs_identify_problem(self):
        cases = []
        spec = json.loads(json.dumps(self.spec))
        spec["edges"][0]["to"] = "missing-id"
        cases.append((spec, "missing-id"))
        spec = json.loads(json.dumps(self.spec))
        spec["nodes"][1]["id"] = "user"
        cases.append((spec, "user"))
        spec = json.loads(json.dumps(self.spec))
        spec["nodes"][1].update(col=0, row=0)
        cases.append((spec, "web"))
        spec = json.loads(json.dumps(self.spec))
        spec["groups"][1]["children"].append("cloud")
        cases.append((spec, "cycle"))
        spec = json.loads(json.dumps(self.spec))
        spec["groups"][1]["children"].append("web")
        cases.append((spec, "web"))
        for spec, expected in cases:
            with self.subTest(expected=expected):
                status, error, _ = self.run_spec(spec, "--check")
                self.assertEqual(status, 1)
                self.assertIn(expected, error)

    def test_custom_theme_changes_colour(self):
        theme = json.loads((SCRIPT.parent.parent / "themes/ibm.json").read_text())
        theme["domains"]["compute"]["primary"] = "#123456"
        path = self.path / "brand.json"
        path.write_text(json.dumps(theme))
        status, error, out = self.run_spec(None, "--theme", str(path))
        self.assertEqual(status, 0, error)
        self.assertIn("#123456", Path(str(out) + ".svg").read_text())
        self.assertIn("#123456", Path(str(out) + ".drawio").read_text())

    def test_special_labels_survive_xml(self):
        label = '&<>"'
        self.spec["nodes"][0]["label"] = label
        self.spec["nodes"][0]["sublabel"] = label
        self.spec["title"] = label
        status, error, out = self.run_spec()
        self.assertEqual(status, 0, error)
        svg = ET.parse(str(out) + ".svg")
        self.assertIn(label, [node.text for node in svg.findall(".//" + SVG + "text")])
        drawio = ET.parse(str(out) + ".drawio")
        values = [node.get("value", "") for node in drawio.findall(".//mxCell")]
        self.assertTrue(any("&amp;&lt;&gt;&quot;" in value for value in values))

    def test_formats_and_check_cli(self):
        status, error, out = self.run_spec(None, "--format", "svg", "--theme", "c4")
        self.assertEqual(status, 0, error)
        self.assertTrue(Path(str(out) + ".svg").exists())
        self.assertFalse(Path(str(out) + ".drawio").exists())
        self.spec["edges"][0]["to"] = "bad-endpoint"
        path = self.path / "broken.json"
        path.write_text(json.dumps(self.spec))
        result = subprocess.run([sys.executable, str(SCRIPT), str(path), "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("bad-endpoint", result.stderr)


if __name__ == "__main__":
    unittest.main()
