import sys, pickle
from emplaka import Tree, Node
from copy import deepcopy
from math import factorial as fact
from math import sqrt, floor, ceil


# Permite que a função recursiva Node.get_endnodes() faça o seu trabalho até o fim.
sys.setrecursionlimit(10000)


# Loops until expanding the tree has no effect (i.e. generates no additional Nodes).
def generate_full_tree(tree):
	tree.set_kernel()
	previous_nodelist = list()
	while (previous_nodelist != tree.nodes):
		previous_nodelist = tree.nodes.copy()
		tree.expand()


# Generates the list of reachable nodes for all 100 Nodes from (0,0) to (9,9).
def generate_endnodes_lists(tree):
	for i in range(0, 10):
		for j in range(0, 10):
			node = tree.get_node((i,j))
			node.get_endnodes()


tree = Tree()
generate_full_tree(tree)
generate_endnodes_lists(tree)
with open('database', 'wb') as file:
	pickle.dump(tree, file)