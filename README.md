# Workflow for Running the File

This README provides instructions on how to execute the workflow to train a NN on calorimeter data with raw input data from a simulation of the EPICAL-2 detector.

## Dependencies

- ROOT library (should support TMVA Keras. I used 6.26.10)
- TensorFlow 2.? (we will use  Keras, also has to match that of ROOT sometimes)
- python3.8+ (check version to match that of ROOT version root-config --has-python3 || --python3-version)


## Display raw Data

Raw data can be found on: https://cernbox.cern.ch/s/IMUyyboVMoiWkHP
And should be put in the folder `/data/raw/`.

gps3 refers to the positron simulation and gps6 to the pion simulation both at 20 GeV with a Gaussian spread of 0.3 GeV as stated by the SPS facility.
The root-files contain a CaloOutputWriter folder with a Root TTree called Frames.
Frames stores the pixel hit information in terms of the vectors column, row and lane for every event, i.e. one TTree entry equals one event.
As EPICAL-2 is equipped with two sensors per layer, lane corresponds to a chip in a certain layer.

To Display a 3Dimensional reconstruction of a single event in the calorimeter, Run `root display_raw_data.cxx`. It should make a canvas with the event colored per layer. 

## Process raw Data
Create the folder: `/data/processed`.\
In order to use the raw data for the NN we have to scale down the information for it to efficiently run on the network. For this we will project the event onto the xy plane, and also downscale the image to a chosen quantization. `root convert_raw_data_and_project.cxx` will do this for you. It is now set to downscaling to 32x32. You have to do this for both the gps3 and gps6 data, so you will have two output files named `gps6_xyproj_hist.root` and `gps3_xyproj_hist.root`.


## Create NN model
We now make the NN using `CreateModels.py`. The learning rate batchsize and weight decay rate can also be changed in the training python file but this has to be done specifically. The default model is a cnn with several layers and a binary classification. 

## Train NN 
Run the python file `Train_NN_on_CalorimeterData.py` to train the NN. The File is laid out below to understand the different parts of the file:

1. Import the necessary libraries:

```
   from ROOT import TMVA, TFile, TTree, TCut, gROOT
   from os.path import isfile
   import ROOT
   import os
   import importlib
   import tensorflow as tf 
```

2. Set up TMVA:
<p style="color:red">If this works, probably the rest will too...</p>

```
   TMVA.Tools.Instance()
   TMVA.PyMethodBase.PyInitialize()
```

1. Define the initial parameters:
```
   num_threads = 0  # use default threads
   epochs = 50  # maximum number of epochs used for training
   batch_size = 100
   instance = '128by128'
   imgSize = 128*128
   data_dir = '../../data/processed/'+instance+'_full/'
   results_dir = '../../results/'+instance+'/'
   model_name = '../../build/model'+instance+'.h5'
   model = tf.keras.models.load_model(model_name)
   useKerasCNN = True
   writeOutputFile = True
   new_learning_rate = 0.001
   optimizer = model.optimizer
   optimizer.learning_rate = new_learning_rate
   model.compile(optimizer=optimizer, loss='binary_crossentropy', metrics=['accuracy'])
   model.save(model_name)
   trained_model_name = '../../build/trained_model_'+instance+'.h5'
```

1. Load data for training and testing:
```   
   data_gps3 = TFile.Open(data_dir+'gps3_xyproj_hist.root')
   data_gps6 = TFile.Open(data_dir+'gps6_xyproj_hist.root')
   outputFile = TFile.Open(results_dir+"TMVA_CNN_ClassificationOutput.root", "RECREATE")
   signalTree = data_gps6.Get("projdata")
   backgroundTree = data_gps3.Get("projdata")
   dataloader = TMVA.DataLoader('dataset')
```

1. Enable multi-threading:
```
   hasGPU = ROOT.gSystem.GetFromPipe("root-config --has-tmva-gpu") == "yes"
   hasCPU = ROOT.gSystem.GetFromPipe("root-config --has-tmva-cpu") == "yes"
   if num_threads >= 0:
       ROOT.EnableImplicitMT(num_threads)
       if (num_threads > 0):
           ROOT.gSystem.Setenv("OMP_NUM_THREADS", str(num_threads))
   else:
       ROOT.gSystem.Setenv("OMP_NUM_THREADS", "1")
   print("Running with nthreads  = ", ROOT.GetThreadPoolSize())
```

1. Create TMVA Factory:
```
   factory = TMVA.Factory('TMVA_CNN_Classification', outputFile, '!V:!Silent:Color:DrawProgressBar:Transformations=None:!Correlations:AnalysisType=Classification')
```

1. Declare DataLoader:
```
   loader = TMVA.DataLoader("dataset")
```

1. Setup Dataset:
```
   nEventsBkg = backgroundTree.GetEntries()
   nEventsSig = signalTree.GetEntries()
   signalWeight = 1.0
   backgroundWeight = 1.0
   loader.AddSignalTree(signalTree, signalWeight)
   loader.AddBackgroundTree(backgroundTree, backgroundWeight)
   loader.AddVariablesArray("vars", imgSize)
   mycuts = ""
   mycutb = ""
   nTrainSig = 0.8 * nEventsSig
   nTrainBkg = 0.8 * nEventsBkg
   nTestSig = 0.2 * nEventsSig
   nTestBkg = 0.2 * nEventsBkg
   loader.PrepareTrainingAndTestTree(
       ROOT.TCut(''),
       'nTrain_Signal=nTrainSig:'
       'nTrain_Background=nTrainBkg:'
       'nTest_Signal=nTestSig'
       'nTest_Background=nTestBkg'
       'SplitMode=Random:'
       'NormMode=NumEvents:!V:'
       'CalcCorrelations=False:Correlations=False'
   )
```

1. Book and train the Deep Neural Network:
```
   if useKerasCNN:
       ROOT.Info("TMVA_CNN_Classification", "Building convolutional keras model")
       if not os.path.exists(model_name):
           raise FileNotFoundError("Error creating Keras model file - skip using Keras")
       else:
           ROOT.Info("TMVA_CNN_Classification", "Booking convolutional keras model")
           factory.BookMethod(loader, TMVA.Types.kPyKeras, 'PyKeras', 'H:!V:VarTransform=None:FilenameModel={}:FilenameTrainedModel={}:NumEpochs={}:BatchSize={}:TriesEarlyStopping=20'.format(model_name,trained_model_name,epochs,batch_size))
```

1.  Train the methods:
```
    factory.TrainAllMethods()
```

1.  Test and evaluate the methods:
```
    factory.TestAllMethods()
    factory.EvaluateAllMethods()
```

1.   Plot the ROC curve:
```
    c1 = factory.GetROCCurve(loader)
    c1.Draw()
```

1.   Close the output file:
```
    outputFile.Close()
```

For successful execution, please ensure you have the necessary dependencies installed and follow the provided instructions.

## Acknowledgements
Thanks to Tim Rogoschinski of the Institut für Kernphysik
Goethe Universität Frankfurt for the raw data from the epical-2 simulation.
