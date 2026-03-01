# /drawio — Chemical Engineering Process Flow Diagrams in Draw.io

When creating or updating process flow diagrams (PFDs) for this project, generate `.drawio` XML files following these conventions. The diagrams should be publication-quality, suitable for engineering journals and technical reports.

## File Structure

Every `.drawio` file must follow this skeleton:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" compressed="false">
  <diagram id="pfd" name="Process Flow Diagram">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1"
                  tooltips="1" connect="1" arrows="1" fold="1" page="1"
                  pageScale="1" pageWidth="1100" pageHeight="850"
                  math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- All diagram content here -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

- Always set `compressed="false"` for version-control-friendly files.
- Cell `id="0"` and `id="1"` are mandatory structural cells; never omit them.
- All content cells use `parent="1"` (or a group cell ID for children).

## ID Conventions

Use descriptive, prefixed IDs for all cells:

| Element | ID pattern | Example |
|---------|-----------|---------|
| Equipment | `{PREFIX}_{name}` | `TOD_Reactor`, `DIST_Column1` |
| Stream edge | `s_{from}_{to}` | `s_feed_splitter`, `s_TOD_mixer` |
| Label text | `lbl_{name}` | `lbl_title`, `lbl_stream4` |
| Group | `grp_{section}` | `grp_downstream`, `grp_pyrolysis` |

## Equipment Shapes

Use these styles for standard chemical engineering unit operations. All equipment uses `html=1;whiteSpace=wrap;fontSize=10;fontStyle=1;` as base style.

### Reactors (fill: `#fff2cc`, stroke: `#d6b656`)

```xml
<!-- Generic reactor (rectangle) -->
<mxCell id="R101" value="R-101&lt;br&gt;&lt;i style='font-weight:normal'&gt;Pyrolyzer&lt;/i&gt;"
        style="rounded=0;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=10;fontStyle=1;"
        vertex="1" parent="1">
  <mxGeometry x="200" y="150" width="120" height="70" as="geometry"/>
</mxCell>
```

### Distillation Columns (fill: `#e1d5e7`, stroke: `#9673a6`)

```xml
<!-- Distillation column (tall cylinder) -->
<mxCell id="T101" value="T-101&lt;br&gt;&lt;i style='font-weight:normal'&gt;Fractionator&lt;/i&gt;"
        style="shape=cylinder3;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;fontSize=10;fontStyle=1;boundedLbl=1;size=10;direction=south;"
        vertex="1" parent="1">
  <mxGeometry x="400" y="100" width="60" height="160" as="geometry"/>
</mxCell>
```

### Heat Exchangers (fill: `#dae8fc`, stroke: `#6c8ebf`)

```xml
<!-- Heat exchanger (circle) -->
<mxCell id="E101" value="E-101"
        style="ellipse;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=10;fontStyle=1;aspect=fixed;"
        vertex="1" parent="1">
  <mxGeometry x="300" y="170" width="50" height="50" as="geometry"/>
</mxCell>
```

### Mixers and Splitters (fill: `#d5e8d4`, stroke: `#82b366`)

```xml
<!-- Mixer (small circle) -->
<mxCell id="MX101" value="M"
        style="ellipse;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=9;fontStyle=1;aspect=fixed;"
        vertex="1" parent="1">
  <mxGeometry x="150" y="175" width="40" height="40" as="geometry"/>
</mxCell>

<!-- Splitter (diamond) -->
<mxCell id="SP101" value="S"
        style="rhombus;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=9;fontStyle=1;aspect=fixed;"
        vertex="1" parent="1">
  <mxGeometry x="100" y="170" width="50" height="50" as="geometry"/>
</mxCell>
```

### Compressors and Pumps (fill: `#f8cecc`, stroke: `#b85450`)

```xml
<!-- Compressor (trapezoid) -->
<mxCell id="C101" value="C-101"
        style="shape=trapezoid;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontSize=10;fontStyle=1;perimeter=trapezoidPerimeter;size=0.15;"
        vertex="1" parent="1">
  <mxGeometry x="250" y="170" width="80" height="50" as="geometry"/>
</mxCell>
```

### Feed and Product Streams (fill: `#f5f5f5`, stroke: `#666666`)

```xml
<!-- Feed stream source (rounded rectangle, light gray) -->
<mxCell id="FEED" value="HDPE Feed&lt;br&gt;250 tpd"
        style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontSize=10;fontStyle=0;dashed=1;"
        vertex="1" parent="1">
  <mxGeometry x="10" y="170" width="80" height="50" as="geometry"/>
</mxCell>

<!-- Product stream sink (rounded rectangle) -->
<mxCell id="PROD_eth" value="Ethylene"
        style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontSize=10;fontStyle=0;"
        vertex="1" parent="1">
  <mxGeometry x="900" y="100" width="80" height="40" as="geometry"/>
</mxCell>
```

### Grinders, Screens, Cyclones (fill: `#ffe6cc`, stroke: `#d79b00`)

```xml
<!-- Solids handling equipment (hexagon) -->
<mxCell id="GR101" value="GR-101&lt;br&gt;&lt;i style='font-weight:normal'&gt;Grinder&lt;/i&gt;"
        style="shape=hexagon;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=10;fontStyle=1;perimeter=hexagonPerimeter2;size=0.15;"
        vertex="1" parent="1">
  <mxGeometry x="150" y="160" width="100" height="60" as="geometry"/>
</mxCell>
```

## Equipment Color Palette Summary

| Category | Fill | Stroke | Used for |
|----------|------|--------|----------|
| Reactors | `#fff2cc` | `#d6b656` | Pyrolyzers, RYield, FCC, Hydrocracker |
| Separation | `#e1d5e7` | `#9673a6` | Distillation columns, flash drums |
| Heat transfer | `#dae8fc` | `#6c8ebf` | Heat exchangers, coolers, heaters |
| Mixing/Splitting | `#d5e8d4` | `#82b366` | Mixers, splitters, junctions |
| Compression | `#f8cecc` | `#b85450` | Compressors, pumps, turbines |
| Solids handling | `#ffe6cc` | `#d79b00` | Grinders, screens, cyclones, conveyors |
| Feed/Product | `#f5f5f5` | `#666666` | Stream sources and sinks |
| Utility | `#e6e6e6` | `#999999` | Utility streams (N2, H2, cooling water) |

## Stream (Edge) Styles

### Process stream (main flow)

```xml
<mxCell id="s1" value=""
        style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;strokeWidth=2;strokeColor=#333333;"
        edge="1" parent="1" source="MX101" target="R101">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

### Utility / auxiliary stream (dashed, thinner)

```xml
<mxCell id="s_util" value=""
        style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=classic;endFill=1;strokeWidth=1;strokeColor=#999999;dashed=1;dashPattern=5 5;"
        edge="1" parent="1" source="UTIL_N2" target="R101">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

### Recycle stream (dashed, colored)

```xml
<mxCell id="s_rec" value=""
        style="edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;endFill=1;strokeWidth=1.5;strokeColor=#0072B2;dashed=1;dashPattern=8 4;"
        edge="1" parent="1" source="T101" target="MX101">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

### Stream label (placed near edge)

```xml
<mxCell id="lbl_s1" value="&lt;font style='font-size:8px'&gt;S-01&lt;br&gt;10,417 kg/hr&lt;/font&gt;"
        style="text;html=1;align=center;verticalAlign=middle;strokeColor=none;fillColor=none;fontSize=8;fontColor=#333333;"
        vertex="1" parent="1">
  <mxGeometry x="175" y="155" width="70" height="30" as="geometry"/>
</mxCell>
```

## Section Groups

Use dashed containers to group related unit operations by technology:

```xml
<mxCell id="grp_tod" value="TOD Section"
        style="rounded=1;whiteSpace=wrap;html=1;container=1;collapsible=0;fillColor=none;strokeColor=#d6b656;fontSize=11;fontStyle=1;verticalAlign=top;spacingTop=2;dashed=1;dashPattern=8 4;strokeWidth=1.5;"
        vertex="1" parent="1">
  <mxGeometry x="80" y="80" width="350" height="220" as="geometry"/>
</mxCell>
<!-- Children use parent="grp_tod" with coordinates relative to the group -->
```

## Layout Guidelines

1. **Flow direction**: Left to right for the main process. Feed on the left, products on the right.
2. **Grid alignment**: Snap to 10px grid. Keep equipment centers on grid lines.
3. **Spacing**: Minimum 60px between equipment horizontally, 40px vertically.
4. **Parallel paths**: Stack vertically with equal spacing.
5. **Avoid crossings**: Route streams to minimize edge crossings. Use waypoints when needed.
6. **Hierarchy**: Upstream technologies (TOD, CP, CPY, PLASMA) on the left; downstream (DISTILLATION, HC, FCC) on the right.

## Labeling Rules

1. **Equipment labels** use HTML format: `"ID&lt;br&gt;&lt;i&gt;Name&lt;/i&gt;"` (bold ID, italic name below)
2. **Stream labels** include stream number and flow rate where relevant
3. **Title**: Add a text cell at the top with the diagram title (fontSize=16, fontStyle=1)
4. **No overlapping labels**: Ensure text does not overlap equipment or streams
5. **Units**: Always include units in operating condition annotations (e.g., "500 C", "1 atm", "250 tpd")

## Checklist Before Saving

1. File uses `compressed="false"` for version control
2. All cells have unique IDs following naming conventions
3. Equipment colors match the palette above
4. Process streams are solid (strokeWidth=2), utility streams are dashed
5. Flow direction is left-to-right
6. Equipment labels include both ID and descriptive name
7. Edge `source` and `target` reference valid cell IDs
8. Section groups use dashed borders with technology-appropriate stroke color
9. Title text is present at the top of the diagram
10. No overlapping elements; minimum spacing maintained
