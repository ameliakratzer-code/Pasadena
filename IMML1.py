import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
import pandas as pd
import sys
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

# Two command line arguments: name of folder, name of files 

df = pd.read_csv('/Users/ameliakratzer/Desktop/LinInterpolation/ML/COOEvents.csv')
dfX = df.iloc[:-1]
dfY = df.iloc[[-1]]
# X = distances and column 2 (first event IMs)
X = dfX[:, [1, 2]]
y = dfY.iloc[:, 2]
# First try without log normalizing the IM vals
Xscaler = MinMaxScaler()
Yscaler = MinMaxScaler()
X_trainU, X_testU, y_trainU, y_testU = train_test_split(X, y, test_size=0.2, random_state=42)
X_train = Xscaler.fit_transform(X_trainU)
X_test = Xscaler.transform(X_testU)
# Change y_trainU temporarily to 2d array for fit transform, then unravel it
y_train = Yscaler.fit_transform(y_trainU.values.reshape(-1,1)).ravel()
y_test = Yscaler.transform(y_testU.values.reshape(-1,1)).ravel()

BATCH_SIZE = 16
EPOCHS = 40
INPUT_SIZE = 8
OUTPUT_SIZE = 1
model = tf.keras.models.Sequential()
model.add(tf.keras.layers.Dense(32, activation='softplus', input_shape=(INPUT_SIZE,)))

model.add(tf.keras.layers.Dense(64))
model.add(tf.keras.layers.BatchNormalization())
model.add(tf.keras.layers.Activation('softplus'))

model.add(tf.keras.layers.Dense(32))
model.add(tf.keras.layers.BatchNormalization())
model.add(tf.keras.layers.Activation('softplus'))

model.add(tf.keras.layers.Dense(OUTPUT_SIZE , activation='sigmoid')) 

optimize = tf.keras.optimizers.Adam(learning_rate=0.001)
model.compile(optimizer = optimize, loss='mean_squared_error')
history = model.fit(X_train, y_train, batch_size=BATCH_SIZE, epochs=EPOCHS, validation_data=(X_test,y_test))

score = model.evaluate(X_test,y_test,verbose=0)
print(f'Test loss: {score}')
# Error plot
plt.figure(1)
plt.plot(history.history['loss'], color = 'green', label = 'Training Loss')
plt.plot(history.history['val_loss'], color = 'pink', label = 'Testing Loss')
plt.title('Training versus Validation Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.savefig(sys.argv[1] + f'/error{sys.argv[2]}.png')
plt.close()
yPredictionListNorm = model.predict(X_test)
yPredictionList = Yscaler.inverse_transform(yPredictionListNorm.reshape(-1,1)).ravel()
ySimList = Yscaler.inverse_transform(y_test.reshape(-1,1)).ravel()
# Prediction plot
plt.figure(2)
plt.scatter(ySimList, yPredictionList, color='blue')
plt.title('Simulated versus Interpolated Values')
plt.xlabel('Simulated')
plt.ylabel('Interpolated')
plt.savefig(sys.argv[1] + f'/simActual{sys.argv[2]}.png')