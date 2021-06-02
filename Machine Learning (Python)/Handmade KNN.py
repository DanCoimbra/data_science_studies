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
import requests


''' Returns the mean value of a numeric pd.Series'''
def get_mean(series):
	return sum([x for x in series]) / len(series)

''' Returns the standard deviation of a numeric pd.Series'''
def get_std(series, mean):
	return math.sqrt(sum([math.pow(x - mean, 2) for x in series]) / len(series))

''' Convertes a single value into a z-score based on a mean and a standard deviation, returning a float with at most two decimal places. '''
def normalize_value(val, mean, std):
	return int(100 * (val - mean) / std) / 100.0

''' Converts values into z-scores based on a pd.Series's mean and std deviation, assuming they are approximately normally distributed. '''
def normalize_series(series):
	mean = get_mean(series)
	std = get_std(series, mean)
	normalized = [normalize_value(x, mean, std) for x in series]
	return pd.Series(normalized)

''' Returns a pd.DataFrame with normalized data.  '''
def normalize_dataframe(df):
	numerics = [normalize_series(series) for name, series in df.items() if series.dtype != 'object']
	textuals = [series for name, series in df.items() if series.dtype == 'object']
	numerics.extend(textuals)
	df_norm = pd.DataFrame(numerics).transpose()
	df_norm.columns = df.columns
	return df_norm

''' Returns N-dimensional distance between two N-dimensional points. '''
def distance(p1, p2):
	return math.sqrt(sum([math.pow(p[0] - p[1], 2) for p in zip(p1, p2)]))

''' Returns a pd.DataFrame with rows (points) sorted based on their distance to a new point. '''
def sort_df(df, new):
	superlist = [list(series) for name, series in df.iterrows()] # Converts a pd.DataFrame into a list of lists, each containing a row.
	superlist.sort(key=lambda sublist: distance(pd.Series(sublist).iloc[0:4], new))
	return pd.DataFrame(superlist)

''' Returns the most common attribute in a new point's k nearest neighbors. '''
def knn(k, df, new):
	df = sort_df(df, new) # Sorts DataFrame by distance to new point.
	return Counter(df.iloc[:k, -1]).most_common(1)[0][0]


df = pd.read_csv('dataset.txt', header=None, names=['x1', 'x2', 'x3', 'x4', 'y']) # Retrieves database
df = df.sample(frac=1).reset_index(drop=True) # Shuffles database
df = normalize_dataframe(df) # Normalizes database
k = 5

train_data = df.iloc[:-1, :]
test_point = df.iloc[-1, :-1]
correct_result = df.iloc[-1, -1]
prediction = knn(k, train_data, test_point)
print(prediction, correct_result, prediction == correct_result, sep='\n')