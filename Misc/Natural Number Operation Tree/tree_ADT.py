''' Este arquivo define as duas classes usadas no programa Emplaka: "Tree" e "Node".'''

import sys, pickle
from copy import deepcopy
from math import factorial as fact
from math import sqrt, floor, ceil

# Permite que a função recursiva Node.get_endnodes() faça o seu trabalho até o fim.
sys.setrecursionlimit(10000)


class Tree:
	''' Armazena os nódulos.'''
	def __init__(self, nodes=set()):
		self.kernel = set()  # The kernel comprises only the nodes from (0,0) to (9,9).
		self.nodes = nodes


	# Cria os 100 nódulos básicos, de (0,0) a (9,9).
	def set_kernel(self):
		for i in range(0, 10):
			for j in range(0, 10):
				Node((i,j), self) # Nódulos são adicionados à árvore-mãe assim que são criados.


	# Expande a árvore preenchendo cada um de seus nódulos que ainda não foramp nreehcidos, via Node.fill().
	def expand(self):
		static_copy = self.nodes.copy() # A static copy is needed, since the for-loop would otherwise alter the very sequence it is iterating over.
		for node in static_copy:
			if not node.filled:
				node.fill(self)


	def has_node(self, items=tuple()):
		for node in self.nodes:
			if node.items == items:
				return True
		return False


	# Nódulos são individuado por sua n-ordenada no atributo Node.items.
	def get_node(self, items=tuple()):
		for node in self.nodes:
			if node.items == items:
				return node
		return Node()



class Node:
	# Nodes are attached to trees (self.tree) and are automatically added to them upon creation (tree.nodes).
	def __init__(self, items=tuple(), tree=Tree(), filled=False):
		self.items = items  # Nodes are individuated by their tuple self.items; see the Tree methods has_node() and get_node().
		self.tree = tree  # Nodes are attached to a tree.
		tree.nodes.add(self)  # Nodes are automatically added to their tree's node set upon creation.
		self.filled = filled  # This informs whether the Node.fill() method has been applied to this node.
		self.link = dict()  # This informs the shortest route to every reachable Node. The dictionary's keys are Nodes, their corresponding items are lists of operations needed to reach that key Node. This is determined by the Node.fill() method.


	def __str__(self):
		return str(self.items)


	unary_ops = {
					'unary √floor': lambda x: (floor(sqrt(x)),),
					'unary √ceil': lambda x: (ceil(sqrt(x)),),
					'unary !': lambda x: (fact(x),),
					'abs': lambda x: (abs(x),),
				}


	binary_ops = {
					'+': lambda x,y: (x+y,),
					'-': lambda x,y: (x-y,),
					'*': lambda x,y: (x*y,),
					'/floor': lambda x,y: (x//y,),
					'/ceil': lambda x,y: (ceil(x/y),),
					'^': lambda x,y: (x**y,),
					'binary ! (left)': lambda x,y: (fact(x), y),
					'binary ! (right)': lambda x,y: (x, fact(y)),
					'binary √floor (left)': lambda x, y: (floor(sqrt(x)), y),
					'binary √ceil (left)': lambda x, y: (ceil(sqrt(x)), y),
					'binary √floor (right)': lambda x, y: (x, floor(sqrt(y))),
					'binary √ceil (right)': lambda x, y: (x, ceil(sqrt(y)))
				}


	# Fills the node's Node.items attribute by performing arithmetic operations.
	def fill(self, tree=Tree()):
		if self.filled == True:
			return
		self.filled = True
		self.link[self] = list() # No operations are needed to reach oneself.

		# If the Node is unary...
		if len(self.items) == 1:
			x = self.items[0]

			for op, function in Node.unary_ops.items(): # Loops through operation/lambda-function pairs in Node.unary_ops (defined above).
				invalid_op = False
				too_big = False
				if (op == 'unary √floor' or op == 'unary √ceil') and x < 0:
					invalid_op = True
				if op == 'unary !' and x < 0:
					invalid_op = True
				if op == 'unary !' and x > 9:
					too_big = True

				# If the operation is valid and the number is not too big for the operation...
				if not invalid_op and not too_big:
					result = function(x) # function() as defined in the for-loop heading.
					if tree.has_node(result):
						node = tree.get_node(result) # Avoids duplication, i.e., Nodes with the same Node.items attribute.
					else:
						node = Node(result) # If the Node was not already in the tree, a new Node is created.
					self.link[node] = [op] # Adds the one operation needed to reach the newfound Node.

		# If the Node is binary...
		elif len(self.items) == 2:
			x = self.items[0]
			y = self.items[1]

			for op, function in Node.binary_ops.items(): # Loops through operation/lambda-function pairs in Node.binary_ops (defined above).
				invalid_op = False
				too_big = False
				if (op == '/floor' or op == '/ceil') and y == 0:
					invalid_op = True
				if (op == 'binary √floor (left)' or op == 'binary √ceil (left)') and x < 0:
					invalid_op = True
				if (op == 'binary √floor (right)' or op == 'binary √ceil (right)') and y < 0:
					invalid_op = True
				if op == '^' and (x > 9 or y > 9):
					too_big = True
				if op == 'binary ! (left)' and x > 9:
					too_big = True
				if op == 'binary ! (right)' and y > 9:
					too_big = True

				# If the operation is valid and the number is not too big for the operation...
				if not invalid_op and not too_big:
					result = function(x,y) # function() as defined in the for-loop heading.
					if tree.has_node(result): # Avoids duplication, i.e., Nodes with the same Node.items attribute.
						node = tree.get_node(result)
					else:
						node = Node(result) # If the Node was not already in the tree, a new Node is created.
					self.link[node] = [op] # Adds the one operation needed to reach the newfound Node.

	
	# Recursive function that determines every Node which can be reached by the main Node (self).
	# Returns dictionary with node/list pairs, whose keys are Nodes and whose corresponding items are lists specifying the operations needed to reach that Node.
	def get_endnodes(self, prev_no_search=set()):
		prev_no_search.add(self) # The Nodes in prev_no_search will not be searched in the current recursive iteration. It has been sent from earlier iterations.
		link_copy = self.link.copy() # A static copy is needed, since the for-loop would otherwise alter the very sequence it is iterating over.

		for curr_node in link_copy:
			if curr_node not in prev_no_search:
				# no_search_recursive_iteration determines what is not to be searched in the next recursive iteration.
				linked_nodes = set(self.link.keys()) # All nodes already in the main Node's (self) link attribute.
				linked_nodes.remove(self)
				linked_nodes.remove(curr_node)
				no_search_recursive_iteration = prev_no_search.copy() # It expands over the Nodes received in prev_no_search.
				no_search_recursive_iteration.update(linked_nodes) # It expands over Nodes already linked in the main Node's (self) link attribute.
				
				# Retrieves and updates links
				node_return = (curr_node.get_endnodes(no_search_recursive_iteration)).copy() # Recursive call; node_return is a dictionary.
				node_return.update(self.link)  # Eliminates operation-list differences with self.link, favoring self.link's versions.
				for received_node in node_return:
					if received_node not in self.link:  # In case a new node has been found...
						previous_path = self.link[curr_node].copy()  # Gets the main Node's (self) path to the node currently under investigation (curr_node) in the for-loop.
						previous_path += node_return[received_node]  # node_return[received_node] lists the operations needed to go from the investigated node (curr_node) to the received node.
						node_return[received_node] = previous_path # Updates node_return to contain the full path from the main Node (self) to the received node.

				# Finally alters the main Node (self).
				self.link.update(node_return)

		return self.link


	# Provides a way to visualize all Nodes reachable from the main Node (self).
	def paths(self):
		print(f"From {self}, one can reach:")
		for node, oplist in self.link.items():
			print(f"\t Node: {node},")
			print(f"\t\tthrough the operations {oplist}")
			print()