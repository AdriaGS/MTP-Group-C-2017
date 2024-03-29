import RPi.GPIO as GPIO
from lib_nrf24 import NRF24
from math import *
import time
import spidev
import sys
import os.path
import pickle

def decompress(compressed):
	"""Decompress a list of output ks to a string."""
	from cStringIO import StringIO
	# Build the dictionary.
	dict_size = 256
	dictionary = dict((i, chr(i)) for i in xrange(dict_size))
 
	# use StringIO, otherwise this becomes O(N^2)
	# due to string concatenation in a loop
	result = StringIO()
	w = chr(compressed.pop(0))
	result.write(w)
	for k in compressed:
		if k in dictionary:
			entry = dictionary[k]
		elif k == dict_size:
			entry = w + w[0]
		else:
			raise ValueError('Bad compressed k: %s' % k)
		result.write(entry)
 
		# Add w+entry[0] to the dictionary.
		dictionary[dict_size] = w + entry[0]
		dict_size += 1
 
		w = entry
	return result.getvalue()

def decompressionOnTheGo(compressedFile, multiplicationList):

	#Open file to save the transmitted data
	outputFile = open("ReceivedFileCompressed1.txt", "wb")

	new_mulData = [il * 256 for il in multiplicationList]
	toDecompress = [sum(x) for x in zip(compressedFile, new_mulData)]

	str_decompressed = decompress(toDecompress)
	outputFile.write(str_decompressed)
	outputFile.close()


def main():	    
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(24, GPIO.OUT)
	GPIO.output(24,1)
	GPIO.setup(22, GPIO.OUT)
	GPIO.output(22,1)

	print("Receiver")
	pipes = [[0xe7, 0xe7, 0xe7, 0xe7, 0xe7], [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]]
	payloadSize = 32
	channel_RX = 0x40
	channel_TX = 0x45

	#Initializa the radio transceivers with the CE ping connected to the GPIO22 and GPIO24
	radio_Tx = NRF24(GPIO, spidev.SpiDev())
	radio_Rx = NRF24(GPIO, spidev.SpiDev())
	radio_Tx.begin(0, 22)
	radio_Rx.begin(1, 24)

	#We set the Payload Size to the limit which is 32 bytes
	radio_Tx.setPayloadSize(payloadSize)
	radio_Rx.setPayloadSize(payloadSize)

	#We choose the channels to be used for one and the other transceiver
	radio_Tx.setChannel(channel_TX)
	radio_Rx.setChannel(channel_RX)

	#We set the Transmission Rate
	radio_Tx.setDataRate(NRF24.BR_250KBPS)
	radio_Rx.setDataRate(NRF24.BR_250KBPS)

	#Configuration of the power level to be used by the transceiver
	radio_Tx.setPALevel(NRF24.PA_MAX)
	radio_Rx.setPALevel(NRF24.PA_MAX)

	#We disable the Auto Acknowledgement
	radio_Tx.setAutoAck(False)
	radio_Rx.setAutoAck(False)
	radio_Tx.enableDynamicPayloads()
	radio_Rx.enableDynamicPayloads()

	#Open the writing and reading pipe
	radio_Tx.openWritingPipe(pipes[1])
	radio_Rx.openReadingPipe(1, pipes[0])

	#We print the configuration details of both transceivers
	radio_Tx.printDetails()
	print("*------------------------------------------------------------------------------------------------------------*")
	radio_Rx.printDetails()
	print("*------------------------------------------------------------------------------------------------------------*")

	###############################################################################################################################
	###############################################################################################################################
	###############################################################################################################################

	#Flag variables
	original_flag_data = 'A'
	original_flag_control = 'O'
	flag = ""
	flag_n = 0
	ctrl_flag_n = 0

	#Packet related variables
	frame = []
	ctrlFrame = []
	handshake_frame = []
	compressed = []
	multiplicationData = []

	#ACK related variables
	time_ack = 0.5
	receivedPacket = 0
	receivedHandshakePacket = 0
	receivedControlPacket = 0
	receivedLastControlPacket = 0

	start = time.time()
	#We listen for the control packet
	radio_Rx.startListening()
	while not (receivedHandshakePacket):
		str_Handshakeframe = ""

		if radio_Rx.available(0):
			radio_Rx.read(handshake_frame, radio_Rx.getDynamicPayloadSize())

			for c in range(0, len(handshake_frame)):
				str_Handshakeframe = str_Handshakeframe + chr(handshake_frame[c])

			print(str_Handshakeframe)

			#print("Handshake frame: " + str_Controlframe)
			if(len(str_Handshakeframe.split(",")) == 3):
				print("Sending ACK")
				radio_Tx.write(list("ACK"))
				str_hand = str_Handshakeframe
			
			else:
				if(chr(handshake_frame[0]) == 'O'):
					multiplicationData.extend(handshake_frame[1:len(handshake_frame)])
					radio_Tx.write(list("ACK") + list('O'))
					ctrl_flag_n = (ctrl_flag_n + 1) % 10
					receivedHandshakePacket = 1

	print("Handshake done")
	numberOfPackets, numberofControlPackets, n = str_hand.split(",")
	print("The number of control packets that will be transmitted: " + numberofControlPackets)
	print("The number of data packets that will be transmitted: " + numberOfPackets)
	print("maximum value of list: " + n)
	
	#radio_Rx.startListening()

	#For all the control packets that are to be received we send a control ack for every one we receive correctly
	for x in range(0, int(numberofControlPackets)-1):

		ctrl_flag = chr(ord(original_flag_control) + ctrl_flag_n)
		timeout = time.time() + time_ack

		#While we don't receive the expected control packet we keep trying
		while not (receivedControlPacket):
			str_controlFrame = ""
			if radio_Rx.available(0):
				radio_Rx.read(ctrlFrame, radio_Rx.getDynamicPayloadSize())

				#We check if the received packet is the expected one
				if(chr(ctrlFrame[0]) == ctrl_flag):
					multiplicationData.extend(ctrlFrame[1:len(ctrlFrame)])
					radio_Tx.write(list("ACK") + list(ctrl_flag))
					receivedControlPacket = 1
				else:
					#print("Message received but not the expected one -> retransmit please")
					if ctrl_flag_n == 0:
						radio_Tx.write(list("ACK") + list('X'))
					else:
						radio_Tx.write(list("ACK") + list(chr(ord(original_flag_control) + ctrl_flag_n-1)))
					timeout = time.time() + time_ack

		ctrl_flag_n = (ctrl_flag_n + 1) % 10
		receivedControlPacket = 0
		print(x)

	while not (receivedLastControlPacket):
		str_controlFrame = ""
		if radio_Rx.available(0):
			radio_Rx.read(ctrlFrame, radio_Rx.getDynamicPayloadSize())

			#We check if the received packet is the expected one
			if(chr(ctrlFrame[0]) == 'A'):
				compressed.extend(ctrlFrame[1:len(ctrlFrame)])
				radio_Tx.write(list("ACK") + list('A'))
				receivedLastControlPacket = 1
				flag_n = (flag_n + 1) % 10
			else:
				#print("Message received but not the expected one -> retransmit please")
				if ctrl_flag_n == 0:
					radio_Tx.write(list("ACK") + list('X'))
				else:
					radio_Tx.write(list("ACK") + list(chr(ord(original_flag_control) + ctrl_flag_n-1)))
				timeout = time.time() + time_ack

	print("Control Packets received Correctly")

	multiplicationData = list(map(int, multiplicationData))
	if(int(n)>16):
		multiplicationData_mid = [ik * 256 for ik in multiplicationData[len(multiplicationData)/2:len(multiplicationData)]]
		multiplicationData = [sum(xk) for xk in zip(multiplicationData[0:len(multiplicationData)/2], multiplicationData_mid)]

	dec_ready = 0
	add = 0
	for i in range(0,int(numberOfPackets)-1):
		timeout = time.time() + time_ack
		flag = chr(ord(original_flag_data) + flag_n)
		while not (receivedPacket):
			if radio_Rx.available(0):
				#print("RECEIVED PKT")
				radio_Rx.read(frame, radio_Rx.getDynamicPayloadSize())
				if(chr(frame[0]) == flag):
					compressed.extend(frame[1:len(frame)])
					if(dec_ready == 200 + add):
						compressed = list(map(int, compressed))
						decompressionOnTheGo(compressed, multiplicationData[0:len(compressed)])
						add += 50
						dec_ready = 0
						print("On the way to the win")
					radio_Tx.write(list("ACK") + list(flag))
					receivedPacket = 1
				else:
					#print("Wrong message -> asking for retransmission")
					if flag_n == 0:
						radio_Tx.write(list("ACK") + list('J'))
					else:
						radio_Tx.write(list("ACK") + list(chr(ord(original_flag_data) + flag_n-1)))
					timeout = time.time() + time_ack
		dec_ready += 1
		flag_n = (flag_n + 1) % 10
		receivedPacket = 0

	compressed = list(map(int, compressed))
	decompressionOnTheGo(compressed, multiplicationData)
	final = time.time()
	print("Total time: " + str(final-start))

	GPIO.output(22, 0)
	GPIO.output(24, 0)

if __name__ == '__main__':
	main()
