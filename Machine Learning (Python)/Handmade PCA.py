from matplotlib import pyplot as plt
import pydataset as pds
from pandas import Series, DataFrame
import pandas as pd
import numpy as np
import math
import random
import scipy
from copy import deepcopy
from collections import Counter, defaultdict
from scipy.stats import norm
from pprint import pprint


def vector_mean(vectors: list):
	mean = [ sum([v[i] for v in vectors]) / len(vectors) for i in range(len(vectors[0])) ]
	return mean

def dataframe_demean(df):
	for column in df:
		mean = df[column].sum() / df[column].size
		df[column] -= mean
	return df

def singlepoint_gradient_descent(intercept: float, slopes: list, INPUTS: list, OUTPUT: float) -> list:
	guess = intercept + sum([slope * INPUT for slope, INPUT in zip(slopes, INPUTS)])
	error = guess - OUTPUT
	gradient = [2 * error] + [2 * error * INPUT for INPUT in INPUTS]
	return gradient

def minibatch_gradient_descent(df, batchsize: int):
	intercept = -10
	slopes = [-10] * (len(df.columns) - 1)
	for epoch in range(50):
		for batch in range(0, df.shape[0], batchsize):
			gradient_list = [ singlepoint_gradient_descent(intercept, slopes, df.iloc[point, : -1], df.iloc[point, -1]) for point in range(batch, batch + batchsize) if point < df.shape[0] ]
			gradient_mean = vector_mean(gradient_list)
			intercept -= gradient_mean[0] * 0.1
			slopes = [ slope - gradient_mean_component * 0.000001 for slope, gradient_mean_component in zip(slopes, gradient_mean[1:]) ]
		if epoch % 10 == 0:
			plt.plot(df.iloc[ : , 0], [intercept + slopes[0] * x for x in df.iloc[ : , 0]], label={epoch})
	return [intercept] + slopes

original = pd.read_csv('nndb_flat.csv')
df = original.select_dtypes(include=['float64'])

X = [x + 10 for x in range(0,1000)]
Y = [x - 10 + 1000 * math.sin(x) * random.random() for x in X]
D = {'Inputs': X, 'Outputs': Y}
df2 = DataFrame(D, columns=['Inputs', 'Outputs'])
plt.scatter(X,Y, color='black')

#df2 = dataframe_demean(df2)
rv = minibatch_gradient_descent(df2, 10)
intercept = rv[0]
slopes = rv[1:]
plt.plot(df.iloc[ : , 0], [intercept + slopes[0] * x for x in df.iloc[ : , 0]], label='Final')
plt.legend()
plt.show()