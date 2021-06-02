import pickle, time

# Define como serão impressas as listas de operações.
def printlist(L):
	for index in range(0, len(L)):
		if index != len(L) - 1:
			print(L[index], end=',   ')
		else:
			print(L[index])
	print()

# Executa a interface 
def main():
	with open('database', 'rb') as file:
		tree = pickle.load(file)

	print("Bem-vindo à Interface de Soluções do jogo Emplaka.")
	placa = input("Insira um número de placa (4 dígitos): ")
	while (len(placa) != 4 or not placa.isdigit()):
		placa = input("Placa inválida. Insira um número de placa (4 dígitos): ")

	left = (int(placa[0]), int(placa[1]))
	right = (int(placa[2]), int(placa[3]))
	time.sleep(1)
	print(f"\nQuais as soluções para {left[0]} ___ {left[1]} = {right[0]} ___ {right[1]}?")
	time.sleep(2)
	leftnode = tree.get_node(left)
	rightnode = tree.get_node(right)
	leftnode_endnodes = set(leftnode.link.keys())
	rightnode_endnodes = set(rightnode.link.keys())
	solutions = leftnode_endnodes.intersection(rightnode_endnodes)
	i = 1
	for solution in solutions:
		if len(solution.items) == 1:
			print(f"Solution #{i}: {solution.items[0]}.")
			print(f"\tReached from the left through:  ", end='')
			printlist(leftnode.link[solution])
			print(f"\tReached from the right through: ", end='')
			printlist(rightnode.link[solution])
			print()
			i += 1
			time.sleep(1)

main()