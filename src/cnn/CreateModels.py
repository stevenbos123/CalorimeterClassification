import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import SGD, Adam
from tensorflow.keras.layers import Input, Dense, Dropout, Flatten, Conv2D, MaxPooling2D, Reshape, AveragePooling2D, Resizing
imgSize = 128*128
batchsize=100

# example CNN model with input image of size 128by128 for a binary classification
# If you want multiclass you require the SparseCategoricalCrossentropy() by TF.
# The learning rate and weights decay that is set here can be changed in the training file as well, but needs to be called specifically.
m3 = Sequential()
m3.add(Reshape((128,128, 1), input_shape=(imgSize,)))
m3.add(Conv2D(64, kernel_size=(2, 2), kernel_initializer="TruncatedNormal", activation="relu", padding="same"))
m3.add(MaxPooling2D(pool_size=(2, 2)))
m3.add(Conv2D(32, kernel_size=(2, 2), kernel_initializer="TruncatedNormal", activation="relu", padding="same"))
m3.add(MaxPooling2D(pool_size=(4, 4)))
m3.add(Conv2D(128, kernel_size=(2, 2), kernel_initializer="TruncatedNormal", activation="relu", padding="same"))
m3.add(MaxPooling2D(pool_size=(4, 4)))
m3.add(Conv2D(64, kernel_size=(2, 2), kernel_initializer="TruncatedNormal", activation="relu", padding="same"))
m3.add(MaxPooling2D(pool_size=(4, 4)))
m3.add(Flatten())
m3.add(Dense(2, activation="softmax"))
m3.compile(loss="binary_crossentropy", optimizer=Adam(learning_rate=0.001), metrics=["accuracy"])
m3.save("model128by128_1.h5")
m3.summary()

