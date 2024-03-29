'''
lzw.py
Frederik Roenn Stensaeth
10.28.15
A Python implementation of the Lempel-Ziv-Welch compression algorithm.
'''

import sys
# import pickle
import os.path

def compress(text):
	"""
	compress() takes a string and compresses it using the LZW algorithm.
	Returns the compressed string in the form of a list of integers.
	@params: string to be compressed.
	@return: compressed string (list of ints).
	"""
	if text == '':
		return []
	elif type(text) != str:
		printError(2)

	# Creates a list that will hold the integers after compression of the
	# string.
	compressed_lst = []

	# Makes the dictionary to hold our values we map to.
	table = {}
	for i in range(256):
		table[chr(i)] = i

	value = ''
	index = 0
	# Loop over each individual character in the text and keep track of where
	# in the string you are (using the value index). Value keeps track of the
	# longest substring you have seen that is in your table.
	for char in text:
		# Add the latest character to our substring.
		total = value + char
		index += 1
		# If we have seen total before we want to make it our value (aka we
		# want to remember it) and move on to the next character. However,
		# we also need to check if we have reached the end of the string. If
		# we have reached the end, we add the total to our compressed list.
		if total in table:
			value = total

		# However, if we have not seen total before, we add value (the
		# substring we had remembered) to the ditionary and we add total
		# to the dictionary (because we have not seen it before). We then
		# move on to remembering the most recent character.
		else:
			compressed_lst.append(table[value])
			table[total] = len(table)
			value = char

		if index == len(text):
			compressed_lst.append(table[value])
		# print(total) # For testing purposes.

	compressed_str = ''
	for num in compressed_lst:
		# print num
		# print str(num)
		compressed_str += ' ' + str(num)
		# print compressed_str

	return compressed_str.strip()

def decompress(compressed_lst):
	"""
	decompress() takes a list of integers and decompresses it using the LZW
	algorithm. Returns the decompressed string.
	@params: compressed string (list of ints).
	@return: decompressed string.
	"""
	if compressed_lst == []:
		return ''
	elif type(compressed_lst) != list:
		printError(1)
	# We start by reconstructing the dictionary we used to compress the
	# string. However, now the keys are the integers and the values are the 
	# strings.
	table = {}
	for i in range(256):
		table[i] = chr(i)

	prev = str(chr(compressed_lst[0]))
	compressed_lst = compressed_lst[1:]
	decompressed_str = prev
	# Loops over element in the compressed list so that we can decompress it.
	# If an element does not exist in our table it must be premature and
	# hence, the list we were given is invalid --> error.
	# If an element is in the list we retrieve it and add it to our solution.
	# And then make sure to add a new value to our table, which is the
	# previous element plus the first letter of the current string.
	for element in compressed_lst:
		if element == len(table):
			# print prev # For testing purposes.
			string = prev + prev
		elif element not in table:
			printError(1)
		else:
			string = table[element]

		decompressed_str += string

		# Constructs new values to add to our table by taking the previous
		# string and adding the first letter of the current string to it.
		table[len(table)] = prev + string[0]

		prev = string

	return decompressed_str

def printError(num):
	"""
	printError() prints an error and usage message.
	@params: integer to customize the error message (1 if in decompress(),
			 2 if in compress(), anything else for other).
	@return: n/a.
	"""
	if num == 1:
		print('Error. Invalid compressed list given to decompress().')
	elif num == 2:
		print('Error. Invalid string given to compress().')
	else:
		print('Error.')
	print('Usage:')
	print('Compression: $ lzw.py <something>.txt <something>.lzw compress')
	print('Decompression: $ lzw.py <something>.txt <something>.lzw decompress')
	sys.exit()

def printSummary(file1, file2):
	"""
	printSummary() prints out the number of bytes in the original file and in
	the result file.
	@params: two files that are to be checked.
	@return: n/a.
	"""
	# Checks if the files exist in the current directory.
	if (not os.path.isfile(file1)) or (not os.path.isfile(file2)):
		printError(0)

	# Finds out how many bytes in each file.
	f1_bytes = os.path.getsize(file1)
	f2_bytes = os.path.getsize(file2)

	sys.stderr.write(str(file1) + ': ' + str(f1_bytes) + ' bytes\n')
	sys.stderr.write(str(file2) + ': ' + str(f2_bytes) + ' bytes\n')

def main():
	# Makes sure the user has provided the correct number of arguments.

	f = open("ElQuijote.txt", 'rb')
	comp = ''.join(compress(f.read()))
	f.close()

	# pickle.dump(comp, open(sys.argv[2], 'wb'))
	f_comp = open("CompressedFile.txt", 'w')
	f_comp.write(comp)
	f_comp.close()

	printSummary("ElQuijote.txt", "CompressedFile.txt")

	comp_str_list = open("CompressedFile.txt", 'rb').read().split()

	comp_int_lst = []
	for num in comp_str_list:
		comp_int_lst.append(int(num))

	decomp = decompress(comp_int_lst)

	f = open("DecompressedFile.txt", 'w')
	f.write(decomp)
	f.close()

	printSummary("CompressedFile.txt", "DecompressedFile.txt")




if __name__ == '__main__':
	main()