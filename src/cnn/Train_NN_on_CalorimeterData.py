from ROOT import TMVA, TFile, TTree, TCut, gROOT
from os.path import isfile
import ROOT
import os
import importlib
import tensorflow as tf

# Setup TMVA
TMVA.Tools.Instance()
TMVA.PyMethodBase.PyInitialize()
 
# Initial parameters
num_threads = 0  # use default threads
epochs = 50  # maximum number of epochs used for training
batch_size=100
instance = '128by128'       
imgSize = 128*128
data_dir = '../../data/processed/'+instance+'_full/'
results_dir = '../../results/'+instance+'/'
model_name='../../build/model'+instance+'.h5'
model = tf.keras.models.load_model(model_name)
useKerasCNN = True
writeOutputFile = True

# set learning rate or decay rate for the model without creating a new model. (optional)
new_learning_rate = 0.001  
optimizer = model.optimizer
optimizer.learning_rate = new_learning_rate

# Compile the model with the modified optimizer
model.compile(optimizer=optimizer, loss='binary_crossentropy', metrics=['accuracy'])
model.save(model_name)

trained_model_name='../../build/trained_model_'+instance+'.h5'



# Load data for training and testing
data_gps3 = TFile.Open(data_dir+'gps3_xyproj_hist.root')
data_gps6 = TFile.Open(data_dir+'gps6_xyproj_hist.root')
outputFile = TFile.Open(results_dir+"TMVA_CNN_ClassificationOutput.root", "RECREATE")       #outputfile of ROC curve etc
signalTree = data_gps6.Get("projdata")
backgroundTree = data_gps3.Get("projdata")
dataloader = TMVA.DataLoader('dataset')


#GPU never worked for me...
hasGPU = ROOT.gSystem.GetFromPipe("root-config --has-tmva-gpu") == "yes"
hasCPU = ROOT.gSystem.GetFromPipe("root-config --has-tmva-cpu") == "yes"
 

 
 
# do enable MT running
if num_threads >= 0:
    ROOT.EnableImplicitMT(num_threads)
    if (num_threads > 0) :
        ROOT.gSystem.Setenv("OMP_NUM_THREADS", str(num_threads))
else:
    ROOT.gSystem.Setenv("OMP_NUM_THREADS", "1")
 
print("Running with nthreads  = ", ROOT.GetThreadPoolSize())
 
 

 
## Create TMVA Factory
 
# Create the Factory class. Later you can choose the methods
# whose performance you'd like to investigate.
 
# The factory is the major TMVA object you have to interact with. Here is the list of parameters you need to pass
 
# - The first argument is the base of the name of all the output
#   weight files in the directory weight/ that will be created with the
#    method parameters
 
# - The second argument is the output file for the training results
 
# - The third argument is a string option defining some general configuration for the TMVA session.
# For example all TMVA output can be suppressed by removing the "!" (not) in front of the "Silent" argument in the
# option string
 
# - note that we disable any pre-transformation of the input variables and we avoid computing correlations between
# input variables
 
 
factory = TMVA.Factory('TMVA_CNN_Classification', outputFile,
                       '!V:!Silent:Color:DrawProgressBar:Transformations=None:!Correlations:AnalysisType=Classification')

 
## Declare DataLoader(s)
 
# The next step is to declare the DataLoader class that deals with input variables
 
# Define the input variables that shall be used for the MVA training
# note that you may also use variable expressions, which can be parsed by TTree::Draw( "expression" )]
 
# In this case the input data consists of an image of 16x16 pixels. Each single pixel is a branch in a ROOT TTree
 
loader = TMVA.DataLoader("dataset")
 
 
## Setup Dataset(s)
 
# Define input data file and signal and background trees
  
 
# --- Register the training and test trees
nEventsBkg = backgroundTree.GetEntries()
nEventsSig = signalTree.GetEntries()

# global event weights per tree (see below for setting event-wise weights)
signalWeight = 1.0
backgroundWeight = 1.0
 
# You can add an arbitrary number of signal or background trees
loader.AddSignalTree(signalTree, signalWeight)
loader.AddBackgroundTree(backgroundTree, backgroundWeight)
 
## add event variables (image)
## use new method (from ROOT 6.20 to add a variable array for all image data)
loader.AddVariablesArray("vars", imgSize)


# Set individual event weights (the variables must exist in the original TTree)
#    for signal    : factory->SetSignalWeightExpression    ("weight1*weight2");
#    for background: factory->SetBackgroundWeightExpression("weight1*weight2");
# loader->SetBackgroundWeightExpression( "weight" );
 
# Apply additional cuts on the signal and background samples (can be different)
mycuts = ""  # for example: TCut mycuts = "abs(var1)<0.5 && abs(var2-0.5)<1";
mycutb = ""  # for example: TCut mycutb = "abs(var1)<0.5";
 
# Tell the factory how to use the training and testing events
# If no numbers of events are given, half of the events in the tree are used
# for training, and the other half for testing:
#    loader.PrepareTrainingAndTestTree( mycut, "SplitMode=random:!V" );
# It is possible also to specify the number of training and testing events,
# note we disable the computation of the correlation matrix of the input variables
 
nTrainSig = 0.8 * nEventsSig
nTrainBkg = 0.8 * nEventsBkg
nTestSig = 0.2 * nEventsSig
nTestBkg = 0.2 * nEventsBkg

# build the string options for DataLoader::PrepareTrainingAndTestTree
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
 
 
# DataSetInfo              : [dataset] : Added class "Signal"
#    : Add Tree sig_tree of type Signal with 10000 events
#    DataSetInfo              : [dataset] : Added class "Background"
#        : Add Tree bkg_tree of type Background with 10000 events
 

# Booking Methods


#### Booking Deep Neural Network

### Book Convolutional Neural Network in Keras using a generated model

if useKerasCNN:
    ROOT.Info("TMVA_CNN_Classification", "Building convolutional keras model")
    # create python script which can be executed

    if not os.path.exists(model_name):
        raise FileNotFoundError("Error creating Keras model file - skip using Keras")
    else:
        # book PyKeras method only if Keras model could be created
        ROOT.Info("TMVA_CNN_Classification", "Booking convolutional keras model")
        factory.BookMethod(loader, TMVA.Types.kPyKeras, 'PyKeras',       
                'H:!V:VarTransform=None:FilenameModel={}:FilenameTrainedModel={}:NumEpochs={}:BatchSize={}:TriesEarlyStopping=20'.format(model_name,trained_model_name,epochs,batch_size))

## Train Methods
factory.TrainAllMethods()   
 
## Test and Evaluate Methods
factory.TestAllMethods()
 
factory.EvaluateAllMethods()
 
## Plot ROC Curve
c1 = factory.GetROCCurve(loader)
c1.Draw()
 
# close outputfile to save output file
outputFile.Close()
