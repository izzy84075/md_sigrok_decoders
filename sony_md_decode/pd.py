## Copyright (C) 2021 Ryan "Izzy" Bales <izzy84075@gmail.com>

# Sony MD LCD Remote decoder

import sigrokdecode as srd

class SamplerateError(Exception):
    pass

class Decoder(srd.Decoder):
	api_version = 3
	id = 'sony_md_decode'
	name = 'Sony MD Remote Decode'
	longname = 'Sony MD LCD Remote Decoder'
	desc = ''
	license = 'unknown'
	inputs = ['sony_md']
	outputs = ['sony_md_decode']
	tags = ['']
	annotations = (
		('info', 'Info'),
		('message-segment', 'Message Segment'),
		('byte', 'Byte'),
		('data-field', 'Data Field'),
		('debug', 'Debug'),
		('debug-two', 'Debug2'),
	)
	annotation_rows = (
		('informational', 'Informational', (0,)),
		('message-segments', 'Message Segments', (1,)),
		('bytes', 'Bytes', (3,)),
		('fields', 'Data Fields', (2,)),
		('debugs', 'Debugs', (4,)),
		('debugs-two', 'Debugs 2', (5,)),
	)
	
	def putMessageStart(self, messageStartSample):
		self.put(messageStartSample, messageStartSample, self.out_ann,
			[0, ['Message Start', 'S']])

	def putBinaryMSBFirst(self, bitData, startBit, numBits):
		currentBit = startBit
		bitsLeft = numBits
		valueStart = bitData[3][startBit][0]
		valueEnd = bitData[3][(startBit+numBits-1)][2]
		value = "0b"

		while bitsLeft > 0:
			value += str(bitData[3][currentBit][3])
			currentBit += 1
			bitsLeft -= 1
		
		self.put(valueStart, valueEnd, self.out_ann,
			[5, [value]])

	def putValueMSBFirst(self, bitData, startBit, numBits):
		currentBit = startBit
		bitsLeft = numBits
		valueStart = bitData[3][startBit][0]
		valueEnd = bitData[3][(startBit+numBits-1)][2]
		value = 0

		while bitsLeft > 0:
			value <<= 1
			value += bitData[3][currentBit][3]
			currentBit += 1
			bitsLeft -= 1
		
		if numBits % 8 == 0:
			self.put(valueStart, valueEnd, self.out_ann,
				[3, ['Value: 0x%02X' % value]])
			self.debugOutHex += ('0x%02X ' % value)
		elif numBits % 9 == 0:
			self.put(valueStart, valueEnd, self.out_ann,
				[3, ['Value: 0o%03o' % value]])
			self.debugOutHex += ('0o%03o ' % value)
		else:
			self.put(valueStart, valueEnd, self.out_ann,
				[3, ['Value (Low %d bits): 0x%X' % (numBits, value)]])
			self.debugOutHex += ('0x%X ' % value)
	
	def putValueLSBFirst(self, bitData, startBit, numBits):
		currentBit = startBit
		shiftBy = 0
		bitsLeft = numBits
		valueStart = bitData[3][startBit][0]
		valueEnd = bitData[3][(startBit+numBits-1)][2]
		value = 0

		while bitsLeft > 0:
			value += (bitData[3][currentBit][3] << shiftBy)
			shiftBy += 1
			currentBit += 1
			bitsLeft -= 1
		
		if numBits % 8 == 0:
			self.put(valueStart, valueEnd, self.out_ann,
				[3, ['Value: 0x%02X' % value]])
			self.debugOutHex += ('0x%02X ' % value)
		elif numBits % 9 == 0:
			self.put(valueStart, valueEnd, self.out_ann,
				[3, ['Value: 0o%03o' % value]])
			self.debugOutHex += ('0o%03o ' % value)
		else:
			self.put(valueStart, valueEnd, self.out_ann,
				[3, ['Value (Low %d bits): 0x%X' % (numBits, value)]])
			self.debugOutHex += ('0x%X ' % value)

		

	def expandMessage(self, bitData):
		currentBit = 0

		self.putBinaryMSBFirst(bitData, 0, bitData[2])

		self.debugOutHex += str(bitData[2])
		self.debugOutHex += "   "

		if (bitData[2] == 104) or (bitData[2] == 16) :
			self.put(bitData[3][0][0], bitData[3][15][2], self.out_ann,
					[1, ['2-byte message header']])
			self.putValueLSBFirst(bitData, 0, 8)
			self.putValueLSBFirst(bitData, 8, 8)
			currentBit += 16

			self.debugOutHex += "   "
			
			if bitData[3][8][3] == 0:
				self.put(bitData[3][8][0], bitData[3][8][2], self.out_ann,
					[2, ['11-byte Data Block Flag', 'Y11B']])
				self.put(bitData[3][currentBit][0], bitData[3][(currentBit+79)][2], self.out_ann,
					[1, ['10-byte data block']])
				self.putValueLSBFirst(bitData, currentBit, 8)
				self.putValueLSBFirst(bitData, currentBit+8, 8)
				self.putValueLSBFirst(bitData, currentBit+16, 8)
				self.putValueLSBFirst(bitData, currentBit+24, 8)
				self.putValueLSBFirst(bitData, currentBit+32, 8)
				self.putValueLSBFirst(bitData, currentBit+40, 8)
				self.putValueLSBFirst(bitData, currentBit+48, 8)
				self.putValueLSBFirst(bitData, currentBit+56, 8)
				self.putValueLSBFirst(bitData, currentBit+64, 8)
				self.putValueLSBFirst(bitData, currentBit+72, 8)
				self.put(bitData[3][currentBit+80][0], bitData[3][currentBit+87][2], self.out_ann,
					[1, ['Checksum']])
				self.putValueLSBFirst(bitData, currentBit+80, 8)
				self.debugOutHex += "   "
				currentBit += 88
			else:
				self.put(bitData[3][8][0], bitData[3][8][2], self.out_ann,
					[2, ['No 11-byte Data Block Flag', 'N11B']])
			if bitData[3][4][3] == 1:
				self.put(bitData[3][4][0], bitData[3][4][2], self.out_ann,
					[2, ['11-bit Data Block Flag', 'Y11b']])
				self.put(bitData[3][currentBit][0], bitData[3][(currentBit+10)][2], self.out_ann,
					[1, ['11-bit data block']])
				self.putValueLSBFirst(bitData, currentBit, 8)
				self.putValueLSBFirst(bitData, currentBit+8, 3)
				self.debugOutHex += "   "
				currentBit += 11
			else:
				self.put(bitData[3][4][0], bitData[3][4][2], self.out_ann,
					[2, ['No 11-bit Data Block Flag', 'N11b']])
		elif bitData[2] == 115:
			currentBit = 0

			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[1, ['header']])
			self.putValueLSBFirst(bitData, currentBit, 8)
			currentBit += 8

			self.debugOutHex += "   "

			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[1, ['header 2']])
			self.putValueLSBFirst(bitData, currentBit, 8)
			currentBit += 8

			self.debugOutHex += "   "

			self.put(bitData[3][currentBit][0], bitData[3][currentBit+62][2], self.out_ann,
				[1, ['63-bit block']])
			self.putValueLSBFirst(bitData, currentBit, 9)
			self.putValueLSBFirst(bitData, currentBit+9, 9)
			self.putValueLSBFirst(bitData, currentBit+18, 9)
			self.putValueLSBFirst(bitData, currentBit+27, 9)
			self.putValueLSBFirst(bitData, currentBit+36, 9)
			self.putValueLSBFirst(bitData, currentBit+45, 9)
			self.putValueLSBFirst(bitData, currentBit+54, 9)
			currentBit += 63

			self.debugOutHex += "   "

			self.put(bitData[3][currentBit][0], bitData[3][currentBit+17][2], self.out_ann,
				[1, ['18-bit block']])
			self.putValueLSBFirst(bitData, currentBit, 9)
			self.putValueLSBFirst(bitData, currentBit+9, 9)
			currentBit += 18

			self.debugOutHex += "   "

			self.put(bitData[3][currentBit][0], bitData[3][currentBit+8][2], self.out_ann,
				[1, ['9-bit block']])
			self.putValueLSBFirst(bitData, currentBit, 9)
			currentBit += 9

			self.debugOutHex += "   "

			self.put(bitData[3][currentBit][0], bitData[3][currentBit+8][2], self.out_ann,
				[1, ['Checksum']])
			self.putValueLSBFirst(bitData, currentBit, 9)
			currentBit += 9

			#self.debugOutHex += "   "

					
		
		self.put(bitData[0], bitData[1], self.out_ann,
				[4, [self.debugOutHex]])
		self.debugOutHex = ""

	def putMessageEnd(self, messageEndSample):
		self.put(messageEndSample, messageEndSample, self.out_ann,
			[0, ['Message End', 'E']])
	
	def reset(self):
		self.state = 'IDLE'

		self.debugOutHex = ""
		self.debugOutBinary = ""

	def __init__(self):
		self.reset()
	
	def start(self):
		#self.out_python = self.register(srd.OUTPUT_PYTHON)
		self.out_ann = self.register(srd.OUTPUT_ANN)
	
	def decode(self, startsample, endsample, data):
		syncData, bitData, cleanEnd = data
		
		startOfBits = bitData[0]
		endOfBits = bitData[1]
		numberOfBits = bitData[2]
		
		self.putMessageStart(startOfBits)
		#for index, dataBit in enumerate(byteData):
			#self.putDataByte(dataByte)
		self.expandMessage(bitData)
		self.putMessageEnd(endOfBits)
				