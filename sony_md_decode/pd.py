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
		('message-segment', 'Rough Message Segment'),
		('value', 'Value'),
		('data-field', 'Data Field'),
		('debug', 'Debug'),
		('debug-two', 'Debug2'),
		('data-field-negative', 'Data Field (Negative)'),
		('sender-player', 'Message Segment From Player'),
		('sender-remote', 'Message Segment From Remote'),
		('message-segment-2', 'Finer Message Segment'),
	)
	annotation_rows = (
		('informational', 'Informational', (0,)),
		('message-segments', 'Rough Message Segments', (1,)),
		('senders', 'Sender', (7,8,)),
		('message-segments-2', 'Finer Message Segments', (9,)),
		('values', 'Values', (2,)),
		('fields', 'Data Fields', (3,6,)),
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

		self.checksum ^= value
		
		if numBits % 8 == 0:
			self.put(valueStart, valueEnd, self.out_ann,
				[2, ['Value: 0x%02X' % value]])
			self.debugOutHex += ('0x%02X ' % value)
		elif numBits % 9 == 0:
			self.put(valueStart, valueEnd, self.out_ann,
				[2, ['Value: 0o%03o' % value]])
			self.debugOutHex += ('0o%03o ' % value)
		else:
			self.put(valueStart, valueEnd, self.out_ann,
				[2, ['Value (Low %d bits): 0x%X' % (numBits, value)]])
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

		self.checksum ^= value
		self.values.append(value)
		
		if numBits % 8 == 0:
			self.put(valueStart, valueEnd, self.out_ann,
				[2, ['Value: 0x%02X' % value]])
			self.debugOutHex += ('0x%02X ' % value)
		elif numBits % 9 == 0:
			self.put(valueStart, valueEnd, self.out_ann,
				[2, ['Value: 0o%03o' % value]])
			self.debugOutHex += ('0o%03o ' % value)
		else:
			self.put(valueStart, valueEnd, self.out_ann,
				[2, ['Value (Low %d bits): 0x%X' % (numBits, value)]])
			self.debugOutHex += ('0x%X ' % value)

	def putRemoteHeader(self, bitData, currentBit):
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[1, ['Header from remote']])
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[8, ['Remote', 'R']])
		self.putValueLSBFirst(bitData, currentBit, 8)
		if bitData[3][currentBit+1][3] == 1:
			self.put(bitData[3][currentBit+1][0], bitData[3][currentBit+1][2], self.out_ann,
				[3, ['Remote is "new" protocol?']])
		else:
			self.put(bitData[3][currentBit+1][0], bitData[3][currentBit+1][2], self.out_ann,
				[6, ['Remote is "old" protocol?']])
		if bitData[3][currentBit+4][3] == 1:
			self.put(bitData[3][currentBit+4][0], bitData[3][currentBit+4][2], self.out_ann,
				[3, ['Remote HAS data to send?', 'RY']])
		else:
			self.put(bitData[3][currentBit+4][0], bitData[3][currentBit+4][2], self.out_ann,
				[6, ['Remote has NO data to send?', 'RN']])
		if bitData[3][currentBit+7][3] == 1:
			self.put(bitData[3][currentBit+7][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Remote Present?']])
		else:
			self.put(bitData[3][currentBit+7][0], bitData[3][currentBit+7][2], self.out_ann,
				[6, ['Remote NOT Present?']])
	
	def putPlayerHeader(self, bitData, currentBit):
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[1, ['Header from player']])
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[7, ['Player', 'P']])
		self.putValueLSBFirst(bitData, currentBit, 8)
		if bitData[3][currentBit][3] == 0:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit][2], self.out_ann,
				[3, ['Player HAS data to send?', 'PY']])
		else:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit][2], self.out_ann,
				[6, ['Player has NO data to send?', 'PN']])
		if bitData[3][currentBit+4][3] == 1:
			self.put(bitData[3][currentBit+4][0], bitData[3][currentBit+4][2], self.out_ann,
				[3, ['Player ACKs remote has data to send, cedes the bus after header?', 'PAR']])
		else:
			self.put(bitData[3][currentBit+4][0], bitData[3][currentBit+4][2], self.out_ann,
				[6, ['Player does not cede the bus to remote after header?', 'PNR']])
		self.put(bitData[3][currentBit+7][0], bitData[3][currentBit+7][2], self.out_ann,
			[3, ['Player Present?']])

	def expandPlayerDataBlock(self, bitData, currentBit, packetType):
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[9, ['Packet type?']])
		if packetType == 0x01:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Request Remote capabilities?']])
			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[9, ['Which block?']])
			if self.values[3] == 0x01:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['First block, LCD capabilities?']])
			elif self.values[3] == 0x02:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Second block']])
			elif self.values[3] == 0x06:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Sixth block, serial number?']])
		elif packetType == 0xA0:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Track number, player stopped?']])
			self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
				[9, ['Track number']])
			self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
				[3, ['Track number: %d' % self.values[6]]])
		elif packetType == 0xA1:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Track number, playing?']])
			self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
				[9, ['Track number']])
			self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
				[3, ['Track number: %d' % self.values[6]]])
		elif packetType == 0xA2:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Track number, just changed track?']])
			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[9, ['New track number?']])
			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[3, ['New Track number: %d' % self.values[3]]])
			self.put(bitData[3][currentBit+16][0], bitData[3][currentBit+23][2], self.out_ann,
				[9, ['Old track number?']])
			self.put(bitData[3][currentBit+16][0], bitData[3][currentBit+23][2], self.out_ann,
				[3, ['Old Track number: %d' % self.values[4]]])
		elif packetType == 0xC8:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['LCD Text']])
			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[9, ['Which segment?']])
			if self.values[3] == 0x02:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Non-final segment?']])
				self.put(bitData[3][currentBit+24][0], bitData[3][currentBit+31][2], self.out_ann,
					[9, ['String position "1"?']])
				self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
					[9, ['String position "2"?']])
				self.put(bitData[3][currentBit+40][0], bitData[3][currentBit+47][2], self.out_ann,
					[9, ['String position "3"?']])
				self.put(bitData[3][currentBit+48][0], bitData[3][currentBit+55][2], self.out_ann,
					[9, ['String position "4"?']])
				self.put(bitData[3][currentBit+56][0], bitData[3][currentBit+63][2], self.out_ann,
					[9, ['String position "5"?']])
				self.put(bitData[3][currentBit+64][0], bitData[3][currentBit+71][2], self.out_ann,
					[9, ['String position "6"?']])
				self.put(bitData[3][currentBit+72][0], bitData[3][currentBit+79][2], self.out_ann,
					[9, ['String position "7"?']])
			elif self.values[3] == 0x01:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Final segment?']])
				self.put(bitData[3][currentBit+24][0], bitData[3][currentBit+31][2], self.out_ann,
					[9, ['String position "1"?']])
				self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
					[9, ['String position "2"?']])
				self.put(bitData[3][currentBit+40][0], bitData[3][currentBit+47][2], self.out_ann,
					[9, ['String position "3"?']])
				self.put(bitData[3][currentBit+48][0], bitData[3][currentBit+55][2], self.out_ann,
					[9, ['String position "4"?']])
				self.put(bitData[3][currentBit+56][0], bitData[3][currentBit+63][2], self.out_ann,
					[9, ['String position "5"?']])
				self.put(bitData[3][currentBit+64][0], bitData[3][currentBit+71][2], self.out_ann,
					[9, ['String position "6"?']])
				self.put(bitData[3][currentBit+72][0], bitData[3][currentBit+79][2], self.out_ann,
					[9, ['String position "7"?']])
	
	def putPlayerDataBlock(self, bitData, currentBit):
		#put up basic data about the message segment
		self.put(bitData[3][currentBit][0], bitData[3][(currentBit+87)][2], self.out_ann,
			[1, ['Player data block?']])
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+87][2], self.out_ann,
			[7, ['Player', 'P']])

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
			[9, ['Checksum']])
		self.put(bitData[3][currentBit+80][0], bitData[3][currentBit+87][2], self.out_ann,
			[3, ['Checksum, calculated value 0x%02X' % self.checksum]])
		self.putValueLSBFirst(bitData, currentBit+80, 8)

		self.expandPlayerDataBlock(bitData, currentBit, self.values[2])
	
	def putRemoteDataBlockTransfer(self, bitData, currentBit):
		self.put(bitData[3][currentBit][0], bitData[3][currentBit][2], self.out_ann,
			[7, ['Player', 'P']])
		self.put(bitData[3][currentBit+1][0], bitData[3][currentBit+8][2], self.out_ann,
			[8, ['Remote', 'R']])
		self.putValueLSBFirst(bitData, currentBit+1, 8)

	def expandRemoteDataBlock(self, bitData, currentBit, packetType):
		self.put(bitData[3][currentBit+1][0], bitData[3][currentBit+8][2], self.out_ann,
			[9, ['Packet type?']])
		
		if packetType == 0xC0:
			self.put(bitData[3][currentBit+1][0], bitData[3][currentBit+8][2], self.out_ann,
				[3, ['Remote capabilities?']])
			self.put(bitData[3][currentBit+10][0], bitData[3][currentBit+17][2], self.out_ann,
				[9, ['Which block?']])
			if self.values[3] == 0x01:
				self.put(bitData[3][currentBit+10][0], bitData[3][currentBit+17][2], self.out_ann,
					[3, ['First block, LCD capabilities?']])
				self.put(bitData[3][currentBit+19][0], bitData[3][currentBit+26][2], self.out_ann,
					[9, ['Characters displayed?']])
				self.put(bitData[3][currentBit+19][0], bitData[3][currentBit+26][2], self.out_ann,
					[3, ['Characters displayed: %d' % self.values[4]]])

				self.put(bitData[3][currentBit+64][0], bitData[3][currentBit+71][2], self.out_ann,
					[9, ['Pixels tall?']])
				self.put(bitData[3][currentBit+64][0], bitData[3][currentBit+71][2], self.out_ann,
					[3, ['Pixels tall: %d' % self.values[9]]])
				self.put(bitData[3][currentBit+73][0], bitData[3][currentBit+80][2], self.out_ann,
					[9, ['Pixels wide?']])
				self.put(bitData[3][currentBit+73][0], bitData[3][currentBit+80][2], self.out_ann,
					[3, ['Pixels wide: %d' % self.values[10]]])
				self.put(bitData[3][currentBit+82][0], bitData[3][currentBit+89][2], self.out_ann,
					[9, ['Character sets supported?']])
			elif self.values[3] == 0x02:
				self.put(bitData[3][currentBit+10][0], bitData[3][currentBit+17][2], self.out_ann,
					[3, ['Second block']])
			elif self.values[3] == 0x06:
				self.put(bitData[3][currentBit+10][0], bitData[3][currentBit+17][2], self.out_ann,
					[3, ['Sixth block, serial number?']])
	
	def putRemoteDataBlock(self, bitData, currentBit):
		#put up basic data about the transfer
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+98][2], self.out_ann,
			[1, ['Remote Data Block (With timing bits from Player)']])
		self.putRemoteDataBlockTransfer(bitData, currentBit)
		self.putRemoteDataBlockTransfer(bitData, currentBit+9)
		self.putRemoteDataBlockTransfer(bitData, currentBit+18)
		self.putRemoteDataBlockTransfer(bitData, currentBit+27)
		self.putRemoteDataBlockTransfer(bitData, currentBit+36)
		self.putRemoteDataBlockTransfer(bitData, currentBit+45)
		self.putRemoteDataBlockTransfer(bitData, currentBit+54)
		self.putRemoteDataBlockTransfer(bitData, currentBit+63)
		self.putRemoteDataBlockTransfer(bitData, currentBit+72)
		self.putRemoteDataBlockTransfer(bitData, currentBit+81)
		self.put(bitData[3][currentBit+91][0], bitData[3][currentBit+98][2], self.out_ann,
			[9, ['Checksum']])
		self.put(bitData[3][currentBit+91][0], bitData[3][currentBit+98][2], self.out_ann,
			[3, ['Checksum, calculated value 0x%02X' % self.checksum]])
		self.putRemoteDataBlockTransfer(bitData, currentBit+90)

		self.expandRemoteDataBlock(bitData, currentBit, self.values[2])


	def expandMessage(self, bitData):
		currentBit = 0

		self.putBinaryMSBFirst(bitData, 0, bitData[2])

		self.debugOutHex += str(bitData[2])
		self.debugOutHex += "   "

		self.putRemoteHeader(bitData, currentBit)
		currentBit += 8

		self.debugOutHex += "   "

		self.putPlayerHeader(bitData, currentBit)
		currentBit += 8

		self.debugOutHex += "   "
		self.checksum = 0

		if (bitData[3][8][3] == 0) and (bitData[3][12][3] == 0):
			self.putPlayerDataBlock(bitData, currentBit)
			currentBit += 88
		elif (bitData[3][4][3] == 1) and (bitData[3][12][3] == 1):
			self.putRemoteDataBlock(bitData, currentBit)
			currentBit += 99

		self.put(bitData[0], bitData[1], self.out_ann,
				[4, [self.debugOutHex]])
		self.debugOutHex = ""
		self.values = []

	def putMessageEnd(self, messageEndSample):
		self.put(messageEndSample, messageEndSample, self.out_ann,
			[0, ['Message End', 'E']])
	
	def reset(self):
		self.state = 'IDLE'

		self.values = []

		self.checksum = 0

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
				