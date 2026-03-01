(* ::Package:: *)

SetDirectory[NotebookDirectory[]];

data = Import["astonML_features&targets 1.xlsx", "XLSX"][[1]];

(* 	Type	HDPE (w%)	LDPE (w%)	LLDPE (w%)	PP (w%)	PS (w%)	C	H	N	O	S	Reaction temperature	Vapor residence time (s)	Liquid	Gasoline range hydrocarbons	Diesel range hydrocarbons *)

colHDPE = 3;
colLDPE = 4;
colLLDPE = 5;
colPP = 6;
colPS = 7;
colReactionTemperature = 13;
colLiquid = 15;

(* LLDPE has no NumericQ, cannot be standarized. So removing it *)
allColumns = {colHDPE, colLDPE, colPP, colPS, colReactionTemperature, colLiquid};

(*clean data*)
(*all values greater than zero for all columns is Clean 1*)

allPlastics = Select[data, 
    NumericQ[#[[colHDPE]]] && NumericQ[#[[colLDPE]]] &&  NumericQ[#[[colPP]]] && 
    NumericQ[#[[colReactionTemperature]]] && 
    NumericQ[#[[colLiquid]]] &&
    NumericQ[#[[colPS]]] &
][[All, allColumns]];

colHDPENew = 1;
colLDPENew = 2;

(* Standardize the data to zero mean unit variance *)
allPlastics = Standardize[allPlastics];

(*Extract all columns that have hdpe or ldpe > 0*)
(*Random sample is to shuffle them*)
dataWithHDPEOrLDPE = RandomSample@Select[allPlastics, (#[[colHDPENew]]>0)||(#[[colLDPENew]]>0)&][[;;,;;]];
dataWithoutHDPEOrLDPE = RandomSample@Complement[allPlastics,dataWithHDPEOrLDPE];

(*Append 50% of dataWithHDPEOrLDPE with remaining. *)
(*Keep remaining 25 for transfer learning, and remaining for testing*)
take50ReturnRemaining[data_,percent_]:=Module[{val},val = RandomSample[data,Floor[Length[data]*percent]]; {val,Complement[data,val]}];
{RemainingdataWithHDPEOrLDPE50,dataWithHDPEOrLDPE50} = take50ReturnRemaining[dataWithHDPEOrLDPE,0.5];
{RemainingdataWithHDPEOrLDPE251,RemainingdataWithHDPEOrLDPE252} = take50ReturnRemaining[RemainingdataWithHDPEOrLDPE50,0.5];

trainingData = ArrayFlatten[{{dataWithHDPEOrLDPE50},{dataWithoutHDPEOrLDPE}}]; (*combining all data with 50% HDPE,LDPE for generalization and then using transfer learning only on HdLDPE*)
trainingDataVal = ArrayFlatten[{{dataWithHDPEOrLDPE50}}];
transferLearningData = RemainingdataWithHDPEOrLDPE251;
testingData = RemainingdataWithHDPEOrLDPE252;

inputs = {1,2,3,4,5};
outputs = {6};

generalModel = Predict[trainingData-> 6, Method -> "NeuralNetwork", "PerformanceGoal" -> "Quality"];




(* Transfer Learning using the above general model *)
netGraph = First[generalModel]["Model"]["Network"];
lengthOfLayers = Information[netGraph, "LayersCount"];
Keys@Information[netGraph, "Arrays"]
Information[netGraph, "FullSummaryGraphic"]
net = Normal[netGraph][[1]];
truncatedNet = NetTake[net, {1, -2}];
newNet = NetInitialize[NetJoin[truncatedNet,NetChain@<|ToString[lengthOfLayers-2]->LinearLayer[50],ToString[lengthOfLayers-1]->LinearLayer[1]|>]] ;
multipliers = Flatten[{Array[(#->0)&,lengthOfLayers-2],(#->1)&/@{lengthOfLayers,lengthOfLayers-1}}]
transferLearnedNet = NetTrain[newNet,MapThread[<|"Input"->#1,"Output"->List@#2|>&,{transferLearningData[[;;,1;;5]],transferLearningData[[;;,6]]}],
LearningRateMultipliers->multipliers];



NetMeasurements[transferLearnedNet,MapThread[<|"Input"->#1,"Output"->List@#2|>&,{testingData[[;;,1;;5]],testingData[[;;,6]]}],{"RSquared","StandardDeviation"}]


(* Using validation instead *)
ValgeneralModel = Predict[trainingDataVal -> 6, Method -> "NeuralNetwork", ValidationSet->(transferLearningData -> 6), "PerformanceGoal" -> "Quality"];


PredictorMeasurements[ValgeneralModel,testingData->6,{"RSquared","StandardDeviation"}]


(* Custom layers *)
module[rate_] := 
 NetChain[{LinearLayer[50], ElementwiseLayer["GELU"], DropoutLayer[rate, "Method" -> "AlphaDropout"]}];
feToStandardizeInput = FeatureExtraction[trainingData[[All,1;;5]], "StandardizedVector"];
inputEncoder = NetEncoder[{"FeatureExtractor",feToStandardizeInput}];
net = NetChain[
  Join[Table[module[0.0], 15], {LinearLayer[]}],"Input"->inputEncoder];
customNet = NetTrain[net,MapThread[<|"Input"->#1,"Output"->List@#2|>&,{trainingData[[;;,1;;5]],trainingData[[;;,6]]}]];
(*netT = NetTrain[net, trainN, 
  LossFunction -> 
   CrossEntropyLossLayer["Index", 
    "Target" -> NetEncoder[{"Class", Union@Values[train]}]], 
  ValidationSet -> testN, MaxTrainingRounds -> 150, Method -> "SGD"]
  Can use MaxTraininRounds as parameter.
  *)


NetMeasurements[customNet,MapThread[<|"Input"->#1,"Output"->List@#2|>&,{testingData[[;;,1;;5]],testingData[[;;,6]]}],{"RSquared","StandardDeviation"}]


(* Making custom layer function to loop over if desired *)
(* 
generalFunction.
Inputs:
numLayers: Each layer has three layers, linear, activation and dropout.
layerParams: A tuple {linearLayerSize,ActivationType,rate}. 
            Each layer has three layers: 1. LinearLayer of size linearLayerSize.
                                         2. Activation layer of ActivationType (E.g., SELU, ReLU, see ElementwiseLayer for supported types)
                                         3. Dropout Layer of rate rate.   
 validation: Whether to do with validation or with transfer learning. T for validation
 Output:
 {R2,std,trainedNet}
  *)
generalFunction[numLayers_:6,valdation_:T,layerParams_:{50,"SELU",0.01}]:= 
Module[{module,num = layerParams[[1]],activation = layerParams[[2]],rat = layerParams[[3]],customNet,r2,std,feToStandardizeInput,inputEncoder,net},
module[rate_] := 
 NetChain[{LinearLayer[num], ElementwiseLayer[activation], DropoutLayer[rate, "Method" -> "AlphaDropout"]}];
feToStandardizeInput = FeatureExtraction[trainingData[[All,1;;5]], "StandardizedVector"];
inputEncoder = NetEncoder[{"FeatureExtractor",feToStandardizeInput}];
net = NetChain[
  Join[Table[module[rat], numLayers], {LinearLayer[]}],"Input"->inputEncoder];
customNet = NetTrain[net,MapThread[<|"Input"->#1,"Output"->List@#2|>&,{trainingDataVal[[;;,1;;5]],trainingDataVal[[;;,6]]}],ValidationSet->MapThread[<|"Input"->#1,"Output"->List@#2|>&,{transferLearningData[[;;,1;;5]],transferLearningData[[;;,6]]}]];
{r2,std} = NetMeasurements[customNet,MapThread[<|"Input"->#1,"Output"->List@#2|>&,{testingData[[;;,1;;5]],testingData[[;;,6]]}],{"RSquared","StandardDeviation"}];
{activation,r2,std,customNet}]


generalFunction[6,T,{50,"Sigmoid",0.01}] (*for validation*)


generalFunction[6,T,{50,#,0.01}]&/@{"SELU","ReLU", "ELU", "SELU", "GELU", "Swish", "HardSwish", "Mish", "SoftSign", "SoftPlus", "HardTanh", "HardSigmoid", "Sigmoid"}


(*Increasing layers from 50 to 75*)
generalFunction[6,T,{75,#,0.01}]&/@{"SELU","ReLU", "ELU", "SELU", "GELU", "Swish", "HardSwish", "Mish", "SoftSign", "SoftPlus", "HardTanh", "HardSigmoid", "Sigmoid"}


(*Increasing LR 0.01 to 0.001*)
generalFunction[6,T,{50,#,0.01}]&/@{"SELU","ReLU", "ELU", "SELU", "GELU", "Swish", "HardSwish", "Mish", "SoftSign", "SoftPlus", "HardTanh", "HardSigmoid", "Sigmoid"}


generalFunctionTL[numLayersGeneral_:6,numLayersTransfer_:2,layerParams_:{50,"SELU",0.01}]:= 
Module[{module,num = layerParams[[1]],activation = layerParams[[2]],rat = layerParams[[3]],customNet,r2,std,feToStandardizeInput,inputEncoder,net,truncatedNet,newNet,multipliers,transferLearningNet},
module[rate_] := 
 NetChain[{LinearLayer[num], ElementwiseLayer[activation], DropoutLayer[rate, "Method" -> "AlphaDropout"]}];
feToStandardizeInput = FeatureExtraction[trainingData[[All,1;;5]], "StandardizedVector"];
inputEncoder = NetEncoder[{"FeatureExtractor",feToStandardizeInput}];
net = NetChain[
  Join[Table[module[rat], numLayersGeneral], {LinearLayer[]}],"Input"->inputEncoder];
customNet = NetTrain[net,MapThread[<|"Input"->#1,"Output"->List@#2|>&,{trainingData[[;;,1;;5]],trainingData[[;;,6]]}],ValidationSet->MapThread[<|"Input"->#1,"Output"->List@#2|>&,{transferLearningData[[;;,1;;5]],transferLearningData[[;;,6]]}]];
truncatedNet = NetTake[customNet, {1, -2}]; (*Take all layers, skip the last linear layer*)
newNet = NetJoin[truncatedNet,NetChain[Join[Table[module[0.0], numLayersTransfer], {LinearLayer[]}]]];
multipliers = Flatten[{Array[(#->0)&,numLayersGeneral],(#->1)&/@Range[numLayersGeneral +1,numLayersGeneral+numLayersTransfer+1]}];
transferLearningNet =NetTrain[newNet,MapThread[<|"Input"->#1,"Output"->List@#2|>&,{transferLearningData[[;;,1;;5]],transferLearningData[[;;,6]]}],
LearningRateMultipliers->multipliers];
{r2,std} = NetMeasurements[transferLearningNet,MapThread[<|"Input"->#1,"Output"->List@#2|>&,{testingData[[;;,1;;5]],testingData[[;;,6]]}],{"RSquared","StandardDeviation"}];
{activation,r2,std,customNet}];


generalFunctionTL[6,2,{50,"SELU",0.01}]


(*generalFunctionTL[6,2,{50,#,0.01}]&/@{"SELU","ReLU", "Ramp", "LogisticSigmoid", "Tan", "Tanh", "ArcTan", "ArcTanh", "Sin", "Sinh", "ArcSin", "ArcSinh", "Cos", "Cosh", "ArcCos", "ArcCosh", "Cot", "Coth", "ArcCot", "ArcCoth", "Csc", "Csch", "ArcCsc", "ArcCsch", "Sec", "Sech", "ArcSec", "ArcSech", "Haversine", "InverseHaversine", "Gudermannian", "InverseGudermannian", "Log", "Exp", "Sqrt", "CubeRoot", "Abs", "Gamma", "LogGamma", "Erf", "InverseErf", "Erfc", "InverseErfc", "Round", "Floor", "Ceiling", "Sign", "FractionalPart", "IntegerPart", "Unitize", "KroneckerDelta"}*)
(*generalFunctionTL[6,2,{50,#,0.01}]&/@{Ramp[#]& }*)
generalFunctionTL[6,2,{50,#,0.01}]&/@{"SELU","ReLU", "ELU", "SELU", "GELU", "Swish", "HardSwish", "Mish", "SoftSign", "SoftPlus", "HardTanh", "HardSigmoid", "Sigmoid"}


(*Increasing layers from 50 to 75*)
generalFunctionTL[6,2,{75,#,0.01}]&/@{"SELU","ReLU", "ELU", "SELU", "GELU", "Swish", "HardSwish", "Mish", "SoftSign", "SoftPlus", "HardTanh", "HardSigmoid", "Sigmoid"}


(*Increasing LR from 0.01 to 0.001*)
generalFunctionTL[6,2,{50,#,0.001}]&/@{"SELU","ReLU", "ELU", "SELU", "GELU", "Swish", "HardSwish", "Mish", "SoftSign", "SoftPlus", "HardTanh", "HardSigmoid", "Sigmoid"}
