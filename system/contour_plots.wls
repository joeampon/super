#!/usr/bin/env wolframscript

(* ============================================================ *)
(*  Regenerate contour plots with Mathematica                    *)
(*  Uniform color ranges per metric across all panels            *)
(* ============================================================ *)

Print["Starting contour plot generation (uniform ranges)..."];

$baseDir = "/Users/markmw/Github/superStructure/system";
$csvDir = $baseDir <> "/contour_csv/";
$outFile = $baseDir <> "/contours_mathematica.pdf";

(* --- Label lookup --- *)
axisLabel["split_TOD"] = "CP+TOD fraction";
axisLabel["split_CP"] = "TOD fraction (of CP+TOD)";
axisLabel["split_CPY"] = "CPY fraction";
axisLabel["split_PLASMA"] = "PLASMA fraction";
axisLabel["split_HC"] = "HC fraction";

(* --- Row subtitles (fixed variables) --- *)
$subtitle = {
  "CPY frac.=0.50, HC frac.=0.50",
  "TOD frac.=0.50, HC frac.=0.50",
  "TOD frac.=0.50, HC frac.=0.50",
  "TOD frac.=0.50, CPY frac.=0.50",
  "CP+TOD frac.=0.34, HC frac.=0.50",
  "CP+TOD frac.=0.34, HC frac.=0.50",
  "CP+TOD frac.=0.34, CPY frac.=0.50",
  "CP+TOD frac.=0.34, TOD frac.=0.50",
  "CP+TOD frac.=0.34, TOD frac.=0.50"
};

(* --- Panel labels: (a) through (z) then ({) --- *)
$labels = Join[CharacterRange["a", "z"], {"{"}];

(* --- Metric titles --- *)
$metricTitle = {
  "MSP ($/kg feed)",
  Row[{"GWP (kg CO", Subscript["", "2"], "-eq/kg feed)"}],
  Row[{"CAC ($/kg CO", Subscript["", "2"], "-eq)"}]
};

(* --- Color functions --- *)
$cfMSP = (Blend[{
  RGBColor[0.230, 0.299, 0.754],
  RGBColor[0.553, 0.635, 0.916],
  RGBColor[0.748, 0.773, 0.957],
  RGBColor[0.865, 0.865, 0.865],
  RGBColor[0.957, 0.740, 0.665],
  RGBColor[0.914, 0.556, 0.423],
  RGBColor[0.706, 0.016, 0.150]
}, #] &);

$cfGWP = (Blend[{
  RGBColor[0.004, 0.427, 0.173],
  RGBColor[0.196, 0.576, 0.318],
  RGBColor[0.454, 0.768, 0.461],
  RGBColor[0.631, 0.851, 0.608],
  RGBColor[0.780, 0.914, 0.706],
  RGBColor[0.906, 0.961, 0.765],
  RGBColor[1.000, 1.000, 0.898]
}, #] &);

$cfCAC = (Blend[{
  RGBColor[0.267, 0.004, 0.329],
  RGBColor[0.282, 0.141, 0.458],
  RGBColor[0.253, 0.265, 0.530],
  RGBColor[0.163, 0.471, 0.558],
  RGBColor[0.128, 0.567, 0.551],
  RGBColor[0.360, 0.721, 0.361],
  RGBColor[0.544, 0.773, 0.247],
  RGBColor[0.762, 0.876, 0.137],
  RGBColor[0.993, 0.906, 0.144]
}, #] &);

$colorFuncs = {$cfMSP, $cfGWP, $cfCAC};

(* --- Smart label formatter --- *)
fmtLabel[z_] := Which[
  Abs[z] >= 1000, ToString[Round[z]],
  Abs[z] >= 100,  ToString[NumberForm[z, {5, 0}]],
  Abs[z] >= 10,   ToString[NumberForm[z, {4, 1}]],
  Abs[z] >= 1,    ToString[NumberForm[z, {3, 1}]],
  True,           ToString[NumberForm[z, {3, 2}]]
];

(* --- Get sorted CSV files --- *)
$files = Sort[FileNames["*.csv", $csvDir]];
Print["Found ", Length[$files], " CSV files"];

(* ============================================================ *)
(*  FIRST PASS: compute global min/max for each metric           *)
(* ============================================================ *)
Print["Computing global ranges..."];
$allVals = {{}, {}, {}};

Do[
  raw = Import[$files[[fi]], "CSV"];
  dat = Rest[raw];
  Do[
    $allVals[[mi]] = Join[$allVals[[mi]], N[dat[[All, mi + 2]]]];
  , {mi, 3}];
, {fi, Length[$files]}];

(* Global ranges for MSP and GWP: use full min/max *)
$zRange = Table[{Min[$allVals[[mi]]], Max[$allVals[[mi]]]}, {mi, 3}];

(* For CAC: clip to 2nd-98th percentile; ensure positive for log scale *)
Module[{s, n, lo, hi, posMin},
  s = Sort[$allVals[[3]]];
  n = Length[s];
  lo = s[[Max[1, Ceiling[0.02 n]]]];
  hi = s[[Min[n, Floor[0.98 n]]]];
  (* Ensure positive range for log-scale colorbar *)
  posMin = Min[Select[s, # > 0 &]];
  If[lo <= 0, lo = posMin];
  $zRange[[3]] = {lo, hi};
];

Print["  MSP range: ", NumberForm[$zRange[[1, 1]], 4], " to ",
  NumberForm[$zRange[[1, 2]], 4]];
Print["  GWP range: ", NumberForm[$zRange[[2, 1]], 4], " to ",
  NumberForm[$zRange[[2, 2]], 4]];
Print["  CAC range: ", NumberForm[$zRange[[3, 1]], 4], " to ",
  NumberForm[$zRange[[3, 2]], 4]];

(* Compute 8 evenly spaced interior contour levels per metric *)
$levels = Table[
  With[{lo = $zRange[[mi, 1]], hi = $zRange[[mi, 2]]},
    Table[lo + (hi - lo) k/9, {k, 1, 8}]
  ]
, {mi, 3}];

(* Override CAC levels with log-spaced values *)
$levels[[3]] = With[{lo = Log10[$zRange[[3, 1]]], hi = Log10[$zRange[[3, 2]]]},
  Table[lo + (hi - lo) k/9, {k, 1, 8}]
];

(* ============================================================ *)
(*  SECOND PASS: generate all plots with uniform ranges          *)
(* ============================================================ *)
$allRows = Table[
  Module[{raw, hdr, dat, xL, yL, sub},
    Print["  [", fi, "/9] ", FileNameTake[$files[[fi]]]];

    raw = Import[$files[[fi]], "CSV"];
    hdr = raw[[1]];
    dat = Rest[raw];

    xL = axisLabel[hdr[[1]]];
    yL = axisLabel[hdr[[2]]];
    sub = $subtitle[[fi]];

    Table[
      Module[{z, triples, labelIdx, lbl, logzlo, logzhi},
        z = N[dat[[All, mi + 2]]];
        logzlo = Log10[$zRange[[3, 1]]];
        logzhi = Log10[$zRange[[3, 2]]];
        (* For CAC (mi==3): transform z values to log10 space *)
        If[mi == 3, z = Log10[Clip[z, {$zRange[[3, 1]], Infinity}]]];
        triples = Transpose[{N[dat[[All, 1]]], N[dat[[All, 2]]], z}];

        labelIdx = 3 (fi - 1) + mi;
        lbl = "(" <> $labels[[labelIdx]] <> ")";

        With[{cfn = $colorFuncs[[mi]],
              zlo = $zRange[[mi, 1]], zhi = $zRange[[mi, 2]],
              lvls = $levels[[mi]],
              loglo = logzlo, loghi = logzhi},
          ListContourPlot[triples,
            FrameLabel -> {
              {Style[yL, 14, FontFamily -> "Helvetica"], None},
              {Style[xL, 14, FontFamily -> "Helvetica"], None}
            },
            PlotLabel -> Column[{
              Style[Row[{lbl, " ", $metricTitle[[mi]]}], 14, Bold,
                FontFamily -> "Helvetica"],
              Style[sub, 11, GrayLevel[0.4], FontFamily -> "Helvetica"]
            }, Alignment -> Center, Spacings -> 0],
            ColorFunction -> If[mi == 3,
              (cfn[Clip[Rescale[#, {loglo, loghi}], {0, 1}]] &),
              (cfn[Clip[Rescale[#, {zlo, zhi}], {0, 1}]] &)
            ],
            ColorFunctionScaling -> False,
            Contours -> lvls,
            ContourStyle -> Directive[GrayLevel[0.15],
              AbsoluteThickness[0.5]],
            ContourLabels -> If[mi == 3,
              Function[{x, y, z},
                Text[Style[fmtLabel[10^z],
                  12, Bold, FontFamily -> "Helvetica",
                  Background -> Directive[Opacity[0.8, White]]
                ], {x, y}]
              ],
              Function[{x, y, z},
                Text[Style[fmtLabel[z],
                  12, Bold, FontFamily -> "Helvetica",
                  Background -> Directive[Opacity[0.8, White]]
                ], {x, y}]
              ]
            ],
            InterpolationOrder -> 3,
            PlotRange -> If[mi == 3,
              {All, All, {loglo, loghi}},
              {All, All, {zlo, zhi}}
            ],
            PlotLegends -> If[mi == 3,
              BarLegend[
                {cfn, {loglo, loghi}},
                LegendMarkerSize -> {16, 210},
                LabelStyle -> Directive[11, FontFamily -> "Helvetica"],
                Ticks -> Table[{v, fmtLabel[10^v]}, {v, lvls}]
              ],
              BarLegend[
                {cfn, {zlo, zhi}},
                LegendMarkerSize -> {16, 210},
                LabelStyle -> Directive[11, FontFamily -> "Helvetica"]
              ]
            ],
            Frame -> True,
            FrameStyle -> Directive[GrayLevel[0.15],
              AbsoluteThickness[0.8]],
            FrameTicksStyle -> Directive[11, FontFamily -> "Helvetica"],
            ImageSize -> 280,
            AspectRatio -> 1,
            PlotRangePadding -> None
          ]
        ]
      ]
    , {mi, 3}]
  ]
, {fi, Length[$files]}];

(* --- Assemble and export --- *)
Print["Assembling grid..."];
$grid = Grid[$allRows,
  Spacings -> {1.5, 1},
  Alignment -> {Center, Center}
];

Print["Exporting to PDF..."];
Export[$outFile, $grid, "PDF"];

Print["Done! Output: ", $outFile];
