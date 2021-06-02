from matplotlib import pyplot as plt
import pydataset as pds
import pandas as pd
import numpy as np
import math
import random
from collections import Counter
from scipy.stats import norm


def polynomial(INPUT, parameters):
	return sum( [ (parameters[index] * (INPUT**index)) for index in range(len(parameters)) ] )

	
def gradient_descent(INPUT, OUTPUT, parameters):
	intercept_derivative = 2*( (slope * INPUT) - OUTPUT + intercept )
	slope_derivative = 2*( (INPUT**2 * slope) + (intercept * INPUT) - (INPUT * OUTPUT) )
	return intercept_derivative, slope_derivative


def vector_sum(vector_list):
	length = len(vector_list[0])
	assert all([len(vector) == length for vector in vector_list]), "ERROR: Vectors ain't same-sized"
	
	result_vector = [0] * length
	for vector in vector_list:
		for index in range(length):
			result_vector[index] += vector[index]
	
	return result_vector


def vector_div(vector, denominator):
	return [item / denominator for item in vector]


def vector_mult(vector, scalar):
	return [item * scalar for item in vector]


xaxis = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
yaxis = [2, 5, 4, 5, 3, 8, 4, 7, 5, 10, 9, 9, 11, 14, 11, 18, 17, 16, 17, 20, 19]

intercept = -10
slope = -10
learning_rate = 0.001
plt.scatter(xaxis, yaxis, s=6, color='black')

for step in range(1001):
	data_size = len(xaxis)
	gradient_list = [gradient_descent(x, y, [intercept, slope]) for x,y in zip(xaxis, yaxis)]
	gradient_sum = vector_sum(gradient_list)
	gradient_mean = vector_div(gradient_sum, data_size)
	intercept -= gradient_mean[0] * 0.01
	slope -= gradient_mean[1] * 0.001
	print(slope, intercept, end='\n\n\n')
	plt.plot(xaxis, [slope * x + intercept for x in xaxis], color='red', alpha=(step / 1000))

plt.show()