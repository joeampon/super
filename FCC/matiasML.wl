SetDirectory[NotebookDirectory[]];
xls = Import["matiasData.xlsx", {"Data"}];

data = xls[[1;;4, {6, 7, 8, 12, 13, 14, 18, 19, 20, 24, 25, 26}, 
    Join[{2}, 
    Range[
        Position[xls[[1, 3]], "Methane"][[2, 1]],
        Position[xls[[1, 3]], "4-tertButylStyrene"][[2, 1]]
    ]]
]]

headers = Join[{"Cycle"},  xls[[1, 3, 
    Join[{2}, 
    Range[
        Position[xls[[1, 3]], "Methane"][[2, 1]],
        Position[xls[[1, 3]], "4-tertButylStyrene"][[2, 1]]
    ]]]]]


m = 0;
data2 = Flatten[BlockMap[
    Function[{x}, 
        m++;
        Map[
            Join[
                {m},
                #
            ] &,
            x
        ]
    ],
    Flatten[data, 1],
    {3}
],1]

(* Add headers to the first row of data2 *)
data3 = Prepend[data2, headers];

(* Export the data to a CSV file *)


Export["matiasDataClean.csv", data3, "CSV"];

(* Export["matiasData.csv", data2, "CSV *)

xls = Import["fcc_msp_uncertainty.csv"];



p1 = Histogram[xls[[2;;,1]],
    12,
    "PDF",
    ChartStyle -> Directive[Gray, Opacity[0.5]],
    Frame -> {True, True, False, False}
]

distribution = 
    FindDistribution[xls[[2;;,1]]]

p2 = Plot[
    PDF[distribution, x],
    {x, Min[xls[[2;;,1]]], Max[xls[[2;;,1]]]},
    PlotStyle -> Directive[Black, Dashed, Thick],
    PlotRange -> All
]

p3 = Show[p1, p2,
    Frame -> {True, True, False, False},
    FrameLabel -> {"Naphtha MSP ($/tonne)", "Probability Density"},
    ImageSize -> 10*72,
    LabelStyle -> Directive[FontSize -> 24]
]

Export["fcc_msp_uncertainty.png", p3];

NotebookDirectory[]


Information[Flatten]
