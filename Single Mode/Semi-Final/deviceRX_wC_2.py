try:
	import RPi.GPIO as GPIO
	from lib_nrf24 import NRF24
	from math import *
	import time
	import spidev
	import sys
	import os.path
	import numpy as np
	from threading import Thread

	def decompress(compressed):
	    """Decompress a list of output ks to a string."""
	    from cStringIO import StringIO
	 
	    # Build the dictionary.
	    dict_size = 256
	    dictionary = dict((i, chr(i)) for i in xrange(dict_size))
	    # in Python 3: dictionary = {i: chr(i) for i in range(dict_size)}
	 
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

	def decompressionOnTheGo(compressedList, listMax):

		compressedString = ""
		for c in range(0, len(compressedList)):
			compressedString += chr(compressedList[c])

		i = 0
		#compressedList += chr(0)
		strJoin = 0
		compde = []
		x = 0
		j = 0
		bitsMax = int(np.ceil(np.log(listMax+1)/np.log(2)))
		charLength = 8

		while i < (len(compressedString)*8/bitsMax):
		  if x < bitsMax:
			strJoin = (strJoin<<charLength) + ord(compressedString[j])
			x = x + charLength
			j = j + 1;
		  else:
			compde.append(strJoin>>(x-bitsMax))
			strJoin = strJoin & (2**(x-bitsMax)-1)
			i += 1
			x = x - bitsMax

		str_decompressed = decompress(compde)

		#Open file to save the transmitted data
		outputFile = open("RxFile-MTPGroupC.txt", "wb")
		outputFile.write(str_decompressed)
		outputFile.close()


	def main():	    

		start = time.time()
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(3, GPIO.OUT) #LED 2 End-of-File
		GPIO.output(3, 0)

		print("Receiver")
		pipes = [[0xe7, 0xe7, 0xe7, 0xe7, 0xe7], [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]]
		payloadSize = 32
		channel_RX = 30
		channel_TX = 50

		#Initializa the radio transceivers with the CE ping connected to the GPIO22 and GPIO24
		radio_Tx = NRF24(GPIO, spidev.SpiDev())
		radio_Rx = NRF24(GPIO, spidev.SpiDev())
		radio_Tx.begin(0, 22)
		radio_Rx.begin(1, 23)

		#We set the Payload Size to the limit which is 32 bytes
		radio_Tx.setPayloadSize(payloadSize)
		radio_Rx.setPayloadSize(payloadSize)

		#We choose the channels to be used for one and the other transceiver
		radio_Tx.setChannel(channel_TX)
		radio_Rx.setChannel(channel_RX)

		#We set the Transmission Rate
		radio_Tx.setDataRate(NRF24.BR_2MBPS)
		radio_Rx.setDataRate(NRF24.BR_2MBPS)

		#Configuration of the power level to be used by the transceiver
		radio_Tx.setPALevel(NRF24.PA_MIN)
		radio_Rx.setPALevel(NRF24.PA_MIN)

		#CRC Length
		radio_Tx.setCRCLength(NRF24.CRC_8)
		radio_Rx.setCRCLength(NRF24.CRC_8)

		#We disable the Auto Acknowledgement
		radio_Tx.setAutoAck(False)
		radio_Rx.setAutoAck(False)
		radio_Tx.enableDynamicPayloads()
		radio_Rx.enableDynamicPayloads()

		#Open the writing and reading pipe
		radio_Rx.openReadingPipe(0, pipes[0])
		radio_Tx.openWritingPipe(pipes[1])

		#We print the configuration details of both transceivers
		#radio_Tx.printDetails()
		#print("*------------------------------------------------------------------------------------------------------------*")
		#radio_Rx.printDetails()
		#print("*------------------------------------------------------------------------------------------------------------*")

		###############################################################################################################################
		###############################################################################################################################
		###############################################################################################################################

		#Flag variables
		original_flag_data = 'A'
		flag = ""
		flag_n = 0
		ctrl_flag_n = 0

		#Packet related variables
		frame = []
		handshake_frame = []
		compressed = []
		str_compressed = ""

		#ACK related variables
		time_ack = 0.02
		receivedPacket = 0
		receivedHandshakePacket = 0

		radio_Rx.startListening()

		###############################################################################################################################
		###############################################################################################################################
		###############################################################################################################################
			
		#We listen for the control packet
		while not (receivedHandshakePacket):
			str_Handshakeframe = ""

			if radio_Rx.available([0]):
				handshake_frame = []
				radio_Rx.read(handshake_frame, radio_Rx.getDynamicPayloadSize())
				print("Something received")

				for c in range(0, len(handshake_frame)):
					str_Handshakeframe = str_Handshakeframe + chr(handshake_frame[c])

				#print("Handshake frame: " + str_Controlframe)
				if(len(str_Handshakeframe.split(",")) == 3):
					print("Sending ACK")
					radio_Tx.write(list("ACK"))
					numberOfPackets, listLength, listMax = str_Handshakeframe.split(",")
					listLength = int(listLength)
					listMax = int(listMax)
				
				else:
					if(chr(handshake_frame[0]) == original_flag_data):
						print("First data packet received")
						handshake_frame = handshake_frame[1:len(handshake_frame)]
						compressed.extend(handshake_frame)

						radio_Tx.write(list("ACK") + list(original_flag_data))
						flag_n = (flag_n + 1) % 10
						receivedHandshakePacket = 1

		print("The number of data packets that will be transmitted: " + numberOfPackets)
		print("Length of list: " + str(listLength))
		print("Maximum value of list: " + str(listMax))
		bitsMax = int(np.ceil(np.log(listMax+1)/np.log(2)))

		###############################################################################################################################
		###############################################################################################################################
		###############################################################################################################################

		suma = 0

		for i in range(0, int(numberOfPackets)-1):

			timeout = time.time() + time_ack
			flag = chr(ord(original_flag_data) + flag_n)

			while not (receivedPacket):
				if radio_Rx.available([0]):
					feame = []
					radio_Rx.read(frame, radio_Rx.getDynamicPayloadSize())

					if(chr(frame[0]) == flag):
						compressed.extend(frame[1:len(frame)])

						if (((len(compressed)*8) % (bitsMax*300)) == 0):
							print("On the way to win")
							thread = Thread(target = decompressionOnTheGo, args = (compressed, listMax))
							thread.start()
						radio_Tx.write(list("ACK") + list(flag))
						receivedPacket = 1

			flag_n = (flag_n + 1) % 10
			receivedPacket = 0

		###############################################################################################################################
		###############################################################################################################################
		###############################################################################################################################

		thread = Thread(target = decompressionOnTheGo, args = (compressed, listMax))
		thread.start()

		final = time.time()
		totalTime = final - start
		print("Total time: " + str(totalTime))

		print("Number of retransmissions = " + str(suma))

		GPIO.output(3, 1)
		radio_Rx.stopListening()
		radio_Tx.end()
		radio_Rx.end()

		time.sleep(5)
		GPIO.cleanup()

	if __name__ == '__main__':
		main()

except KeyboardInterrupt:
	GPIO.cleanup()
