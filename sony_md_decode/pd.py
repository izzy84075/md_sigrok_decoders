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
		('error', 'Error'),
		('warning', 'Warning'),
		('data-field-unused', 'Data Field (Unused)'),
		('data-field-unknown', 'Data Field (Unknown)'),
		('data-field-static', 'Data Field (Static)'),
	)
	annotation_rows = (
		('informational', 'Informational', (0,)),
		('message-segments', 'Rough Message Segments', (1,)),
		('senders', 'Sender', (7,8,)),
		('message-segments-2', 'Finer Message Segments', (9,)),
		('values', 'Values', (2,)),
		('fields', 'Data Fields', (3,6,12,13,14,)),
		('debugs', 'Debugs', (4,)),
		('debugs-two', 'Debugs 2', (5,)),
		('errors', 'Errors', (10,)),
		('warnings', 'Warnings', (11,)),
	)

	characters = {
		0x00: "<Unusued position>, 0x00",
		0x04: "<minidisc icon>, 0x04",
		0x06: "<group icon>, 0x06",
		0x0B: "<begin half-width katakana>, 0x0B",
		0x0C: "<end half-width katakana>, 0x0C",
		0x14: "<music note icon>, 0x14",

		0x20: "' ', space, 0x20",

		0xFF: "<End of string>, 0xFF",

	}
	
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
		
		return value

	def putStaticByte(self, bitData, currentBit, value, expectedValue):
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[9, ['Static?']])
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[13, ['Static?']])
		if value != expectedValue:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[10, ['Previously static byte is not expected value!']])
	
	def putUnusedByte(self, bitData, currentBit, value, expectedValue):
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[9, ['Unused?']])
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[12, ['Unused?']])
		if value != expectedValue:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[10, ['Previously unused byte is not expected value!']])
		if value != 0x00:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[11, ['Unused byte has non-zero value!']])
	
	def putUnusedBits(self, bitData, currentBit, numBits, value, expectedValue):
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+numBits-1][2], self.out_ann,
			[9, ['Unused?']])
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+numBits-1][2], self.out_ann,
			[12, ['Unused?']])
		if value != expectedValue:
			if numBits == 1:
				self.put(bitData[3][currentBit][0], bitData[3][currentBit+numBits-1][2], self.out_ann,
					[10, ['Previously unused bit is not expected value!']])
			else:
				self.put(bitData[3][currentBit][0], bitData[3][currentBit+numBits-1][2], self.out_ann,
					[10, ['Previously unused bits are not expected value!']])
		if value != 0x00:
			if numBits == 1:
				self.put(bitData[3][currentBit][0], bitData[3][currentBit+numBits-1][2], self.out_ann,
					[11, ['Unused bit has non-zero value!']])
			else:
				self.put(bitData[3][currentBit][0], bitData[3][currentBit+numBits-1][2], self.out_ann,
					[11, ['Unused bits have non-zero value!']])
	
	def putUnknownByte(self, bitData, currentBit, value):
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[9, ['Unknown?']])
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[13, ['Unknown: 0x%02X' % value]])
		if value != 0x00:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[10, ['Unknown byte has non-zero value!']])

	def putRemoteHeader(self, bitData, currentBit):
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[1, ['Header from remote']])
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[8, ['Remote', 'R']])
		self.putValueLSBFirst(bitData, currentBit, 8)

		self.putUnusedBits(bitData, currentBit, 1, (self.values[0] & 0x01), 0)

		if bitData[3][currentBit+1][3] == 1:
			self.put(bitData[3][currentBit+1][0], bitData[3][currentBit+1][2], self.out_ann,
				[3, ['Remote is ready for text']])
		else:
			self.put(bitData[3][currentBit+1][0], bitData[3][currentBit+1][2], self.out_ann,
				[6, ['Remote is NOT ready for text']])
		
		if bitData[3][currentBit+2][3] == 1:
			self.put(bitData[3][currentBit+2][0], bitData[3][currentBit+2][2], self.out_ann,
				[3, ['Remote is EXTRA ready for text?']])
			self.put(bitData[3][currentBit+2][0], bitData[3][currentBit+2][2], self.out_ann,
				[10, ['Weird header, look here']])
		else:
			self.put(bitData[3][currentBit+2][0], bitData[3][currentBit+2][2], self.out_ann,
				[6, ['Remote is NOT EXTRA ready for text?']])

		self.putUnusedBits(bitData, currentBit+3, 1, ((self.values[0] & 0x8) >> 3), 0)

		if bitData[3][currentBit+4][3] == 1:
			self.put(bitData[3][currentBit+4][0], bitData[3][currentBit+4][2], self.out_ann,
				[3, ['Remote HAS data to send', 'RY']])
		else:
			self.put(bitData[3][currentBit+4][0], bitData[3][currentBit+4][2], self.out_ann,
				[6, ['Remote has NO data to send', 'RN']])
		
		self.putUnusedBits(bitData, currentBit+5, 1, ((self.values[0] & 0x20) >> 5), 0)

		if bitData[3][currentBit+6][3] == 1:
			self.put(bitData[3][currentBit+6][0], bitData[3][currentBit+6][2], self.out_ann,
				[3, ['Remote IS Kanji-capable?']])
		else:
			self.put(bitData[3][currentBit+6][0], bitData[3][currentBit+6][2], self.out_ann,
				[6, ['Remote is NOT Kanji-capable?']])

		if bitData[3][currentBit+7][3] == 1:
			self.put(bitData[3][currentBit+7][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Remote Present', 'RP']])
		else:
			self.put(bitData[3][currentBit+7][0], bitData[3][currentBit+7][2], self.out_ann,
				[6, ['Remote NOT Present', 'RNP']])
		
		#if (bitData[3][currentBit+7][3] == 1) and (bitData[3][currentBit+1][3] == 0):
			#self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				#[11, ['Remote present but not active!']])
	
	def putPlayerHeader(self, bitData, currentBit):
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[1, ['Header from player']])
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[7, ['Player', 'P']])
		self.putValueLSBFirst(bitData, currentBit, 8)

		if bitData[3][currentBit][3] == 0:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit][2], self.out_ann,
				[3, ['Player HAS data to send', 'PY']])
		else:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit][2], self.out_ann,
				[6, ['Player has NO data to send', 'PN']])
		
		self.putUnusedBits(bitData, currentBit+1, 3, ((self.values[1] & 0xE) >> 1), 0)

		if bitData[3][currentBit+4][3] == 1:
			self.put(bitData[3][currentBit+4][0], bitData[3][currentBit+4][2], self.out_ann,
				[3, ['Player cedes the bus to remote after header', 'RDB']])
		else:
			self.put(bitData[3][currentBit+4][0], bitData[3][currentBit+4][2], self.out_ann,
				[6, ['Player does NOT cede the bus to remote after header', 'PDB']])
		
		self.putUnusedBits(bitData, currentBit+5, 2, ((self.values[1] & 0x60) >> 5), 0)

		self.put(bitData[3][currentBit+7][0], bitData[3][currentBit+7][2], self.out_ann,
			[3, ['Player Present']])
	
	def putLCDCharacter(self, bitData, currentBit, values, index):
		isFirstOfDouble = lambda x: x in range(0x81, 0x9f) or x in range(0xe0, 0xef)
		isSJISHalfKata = lambda x: x in range(0xa1, 0xdf)
		isPrintable = lambda x: x in range(0x20, 0x7e)

		twoByteStartIndices = []
		charIndex = 0
		while charIndex < len(values):
			if isFirstOfDouble(values[charIndex]):
				twoByteStartIndices.append(charIndex)
				charIndex += 1
			charIndex += 1

		value = values[index]
		nextValue = values[index + 1] if index < len(values) - 1 else None
		if value in self.characters: # self.characters takes priority
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, [self.characters[value]]])
			return
		if index - 1 in twoByteStartIndices: return # The correct character has already been displayed.
		if index in twoByteStartIndices:
			if nextValue is None:
				self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
					[3, ['First byte of 2-byte SJIS sequence']])
			else:
				self.put(bitData[3][currentBit][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, [bytes([value, nextValue]).decode('sjis')]])
		elif isPrintable(value):
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, [bytes([value]).decode('sjis')]])
		elif isSJISHalfKata(value):
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['SJIS half-width katakana - shouldn\'t be possible']])
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[11, ['Probably the second-half of a full-width SJIS, figure out how to decode across message boundaries?']])
		else:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Unknown character']])
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[10, ['Unknown character']])

	def expandPlayerDataBlock(self, bitData, currentBit, packetType):
		self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
			[9, ['Packet type']])
		if packetType == 0x01:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Request Remote capabilities']])

			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[11, ['Unsure']])
			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[9, ['Which block?']])
			if self.values[3] == 0x01:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['First block']])
			elif self.values[3] == 0x02:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Second block, LCD capabilities?']])
			elif self.values[3] == 0x05:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Fifth block']])
			elif self.values[3] == 0x06:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Sixth block?']])
			else:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
			currentBit += 16
		elif packetType == 0x03:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[11, ['Unsure']])
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Scroll control?']])
			
			self.putStaticByte(bitData, currentBit+8, self.values[3], 0x80)

			self.put(bitData[3][currentBit+16][0], bitData[3][currentBit+31][2], self.out_ann,
				[11, ['Unsure']])
			self.put(bitData[3][currentBit+16][0], bitData[3][currentBit+31][2], self.out_ann,
				[9, ['Enable scrolling?']])
			if (self.values[4] == 0x02) and (self.values[5] == 0x80):
				self.put(bitData[3][currentBit+16][0], bitData[3][currentBit+31][2], self.out_ann,
					[3, ['Scrolling: Enabled']])
			elif (self.values[4] == 0x00) and (self.values[5] == 0x00):
				self.put(bitData[3][currentBit+16][0], bitData[3][currentBit+31][2], self.out_ann,
					[3, ['Scrolling: Disabled']])
			else:
				self.put(bitData[3][currentBit+16][0], bitData[3][currentBit+31][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
			
			currentBit += 32
		elif packetType == 0x05:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['LCD Backlight Control']])
			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[9, ['LCD Backlight State']])
			if self.values[3] == 0x00:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['LCD Backlight: Off']])
			elif self.values[3] == 0x7F:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['LCD Backlight: On']])
			else:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
			currentBit += 16
		elif packetType == 0x06:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[11, ['Unsure']])
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['LCD Remote Service Mode Control?']])
			
			if self.values[3] == 0x7F:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['LCD Remote Service Mode End']])
			elif (self.values[3] == 0x00) and (self.values[4] == 0x06) and (self.values[5] == 0x01) and (self.values[6] == 0x03) and (self.values[7] == 0x80):
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+47][2], self.out_ann,
					[11, ['Unsure']])
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+47][2], self.out_ann,
					[3, ['LCD Remote Service Mode All Segments On?']])
			else:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
			currentBit += 16
		elif packetType == 0x08:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[11, ['Unsure']])
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Unknown, seems to be sent before 0xC8 text updates']])
			
			self.putStaticByte(bitData, currentBit+8, self.values[3], 0x80)
			self.putStaticByte(bitData, currentBit+16, self.values[4], 0x07)
			self.putStaticByte(bitData, currentBit+24, self.values[5], 0x80)
			
			currentBit += 32
		elif packetType == 0x09:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[11, ['Unsure']])
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Unknown, seems to be sent before 0xC8 text updates, but not always sent']])
			
			currentBit += 8
		elif packetType == 0x40:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Volume Level']])
			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[9, ['Current Volume Level']])
			if self.values[3] == 0xFF:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Current Volume Level: 32/32']])
			elif self.values[3] < 32:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Current Volume Level: %d/32' % self.values[3]]])
			else:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
			currentBit += 16
		elif packetType == 0x41:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Playback Mode']])
			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[9, ['Current Playback Mode']])
			if self.values[3] == 0x00:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Current Playback Mode: Normal']])
			elif self.values[3] == 0x01:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Current Playback Mode: Repeat All Tracks']])
			elif self.values[3] == 0x02:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Current Playback Mode: One Track, Stop Afterwards']])
			elif self.values[3] == 0x03:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Current Playback Mode: Repeat One Track']])
			elif self.values[3] == 0x04:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Current Playback Mode: Shuffle No Repeats']])
			elif self.values[3] == 0x05:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Current Playback Mode: Shuffle With Repeats']])
			elif self.values[3] == 0x06:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Current Playback Mode: PGM, No Repeats']])
			elif self.values[3] == 0x07:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Current Playback Mode: PGM, Repeat']])
			else:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
			currentBit += 16
		elif packetType == 0x42:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Record Indicator']])
			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[9, ['Record Indicator State']])
			if self.values[3] == 0x00:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Record Indicator: Off']])
			elif self.values[3] == 0x7F:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Record Indicator: On']])
			else:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
			currentBit += 16
		elif packetType == 0x43:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Battery Level Indicator']])
			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[9, ['Battery Level Indicator State']])
			if self.values[3] == 0x00:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Battery Level Indicator: Off']])
			elif self.values[3] == 0x01:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Battery Level Indicator: 1/4 bars, blinking']])
			elif self.values[3] == 0x7F:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Battery Level Indicator: Charging']])
			elif self.values[3] == 0x80:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Battery Level Indicator: Empty, blinking']])
			elif self.values[3] == 0x9F:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Battery Level Indicator: 1/4 bars']])
			elif self.values[3] == 0xBF:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Battery Level Indicator: 2/4 bars']])
			elif self.values[3] == 0xDF:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Battery Level Indicator: 3/4 bars']])
			elif self.values[3] == 0xFF:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Battery Level Indicator: 4/4 bars']])
			else:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
			currentBit += 16
		elif packetType == 0x46:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['EQ/Sound Indicator']])
			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[9, ['EQ/Sound Indicator State']])
			if self.values[3] == 0x00:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['EQ/Sound Indicator: Normal']])
			elif self.values[3] == 0x01:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[11, ['Unsure']])
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['EQ/Sound Indicator: Bass 1?']])
			elif self.values[3] == 0x02:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[11, ['Unsure']])
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['EQ/Sound Indicator: Bass 2?']])
			elif self.values[3] == 0x03:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['EQ/Sound Indicator: Sound 1']])
			elif self.values[3] == 0x04:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['EQ/Sound Indicator: Sound 2']])
			else:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
			currentBit += 16
		elif packetType == 0x47:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Alarm Indicator']])
			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[9, ['Alarm Indicator State']])
			if self.values[3] == 0x00:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Alarm Indicator: Off']])
			elif self.values[3] == 0x7F:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Alarm Indicator: On']])
			else:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
			currentBit += 16
		elif packetType == 0x48:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[11, ['Unsure']])
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Unknown, happens near track changes?']])

			currentBit += 8
		elif packetType == 0x49:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[11, ['Unsure']])
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Unknown, happens 12 packets after a 0x46?']])

			currentBit += 8
		elif packetType == 0x4A:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[11, ['Unsure']])
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Unknown, happens before 0xC8 text updates?']])

			currentBit += 8
		elif packetType == 0xA0:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Track number']])

			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[9, ['Track Number Indicator Enable']])
			if self.values[3] == 0x00:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Track Number Indicator: On']])
			elif self.values[3] == 0x80:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Track Number Indicator: Off']])
			else:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
			
			self.putStaticByte(bitData, currentBit+16, self.values[4], 0x00)
			self.putStaticByte(bitData, currentBit+24, self.values[5], 0x00)
			
			self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
				[9, ['Current Track Number']])
			self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
				[3, ['Current Track Number: %d' % self.values[6]]])
			
			currentBit += 40
		elif packetType == 0xA1:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['LCD Disc Icon Control']])

			self.putStaticByte(bitData, currentBit+8, self.values[3], 0x00)

			self.put(bitData[3][currentBit+16][0], bitData[3][currentBit+23][2], self.out_ann,
				[9, ['LCD Disc Icon Outline']])
			if self.values[4] == 0x00:
				self.put(bitData[3][currentBit+16][0], bitData[3][currentBit+23][2], self.out_ann,
					[3, ['LCD Disc Icon Outline: Off']])
			elif self.values[4] == 0x7F:
				self.put(bitData[3][currentBit+16][0], bitData[3][currentBit+23][2], self.out_ann,
					[3, ['LCD Disc Icon Outline: On']])
			else:
				self.put(bitData[3][currentBit+16][0], bitData[3][currentBit+23][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
			
			self.put(bitData[3][currentBit+24][0], bitData[3][currentBit+31][2], self.out_ann,
				[9, ['LCD Disc Icon Fill Segments Enable']])
			if self.values[5] == 0x00:
				self.put(bitData[3][currentBit+24][0], bitData[3][currentBit+31][2], self.out_ann,
					[3, ['LCD Disc Icon Fill Segments: All disabled']])
			elif self.values[5] == 0x7F:
				self.put(bitData[3][currentBit+24][0], bitData[3][currentBit+31][2], self.out_ann,
					[3, ['LCD Disc Icon Fill Segments: All enabled']])
			else:
				self.put(bitData[3][currentBit+24][0], bitData[3][currentBit+31][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])

			self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
				[9, ['LCD Disc Icon Fill Segment Animation']])
			if self.values[6] == 0x00:
				self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
					[3, ['LCD Disc Icon Fill Segment Animation: No animation, no segments displayed']])
			elif self.values[6] == 0x01:
				self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
					[3, ['LCD Disc Icon Fill Segment Animation: "Fast Spinning" animation']])
			elif self.values[6] == 0x03:
				self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
					[3, ['LCD Disc Icon Fill Segment Animation: "Spinning" animation']])
			elif self.values[6] == 0x7F:
				self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
					[3, ['LCD Disc Icon Fill Segment Animation: No animation, all segments displayed']])
			else:
				self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
			currentBit += 40
		elif packetType == 0xA2:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[11, ['Unsure']])
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Unknown, happens near track changes?']])

			self.putStaticByte(bitData, currentBit+8, self.values[3], 0x01)
			self.putStaticByte(bitData, currentBit+16, self.values[4], 0x01)
			self.putStaticByte(bitData, currentBit+24, self.values[5], 0x7F)

			currentBit += 32
		elif packetType == 0xA5:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[11, ['Unsure']])
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['Unknown, happens after initialization?']])

			self.putStaticByte(bitData, currentBit+8, self.values[3], 0x01)
			self.putStaticByte(bitData, currentBit+16, self.values[4], 0x76)
			self.putStaticByte(bitData, currentBit+24, self.values[5], 0x81)

			currentBit += 32
		elif packetType == 0xC8:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[3, ['LCD Text']])

			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[11, ['Unsure']])
			self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
				[9, ['Which segment?']])
			if self.values[3] == 0x02:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Non-final segment?']])
			elif self.values[3] == 0x01:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[3, ['Final segment?']])
			else:
				self.put(bitData[3][currentBit+8][0], bitData[3][currentBit+15][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
				
			self.putStaticByte(bitData, currentBit+16, self.values[4], 0x00)

			splicedValues = self.values[5:12]
			self.put(bitData[3][currentBit+24][0], bitData[3][currentBit+31][2], self.out_ann,
				[9, ['String position 1']])
			self.putLCDCharacter(bitData, currentBit+24, splicedValues, 0)
			self.put(bitData[3][currentBit+32][0], bitData[3][currentBit+39][2], self.out_ann,
				[9, ['String position 2']])
			self.putLCDCharacter(bitData, currentBit+32, splicedValues, 1)
			self.put(bitData[3][currentBit+40][0], bitData[3][currentBit+47][2], self.out_ann,
				[9, ['String position 3']])
			self.putLCDCharacter(bitData, currentBit+40, splicedValues, 2)
			self.put(bitData[3][currentBit+48][0], bitData[3][currentBit+55][2], self.out_ann,
				[9, ['String position 4']])
			self.putLCDCharacter(bitData, currentBit+48, splicedValues, 3)
			self.put(bitData[3][currentBit+56][0], bitData[3][currentBit+63][2], self.out_ann,
				[9, ['String position 5']])
			self.putLCDCharacter(bitData, currentBit+56, splicedValues, 4)
			self.put(bitData[3][currentBit+64][0], bitData[3][currentBit+71][2], self.out_ann,
				[9, ['String position 6']])
			self.putLCDCharacter(bitData, currentBit+64, splicedValues, 5)
			self.put(bitData[3][currentBit+72][0], bitData[3][currentBit+79][2], self.out_ann,
				[9, ['String position 7']])
			self.putLCDCharacter(bitData, currentBit+72, splicedValues, 6)

			currentBit += 80
		else:
			self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
				[10, ['UNRECOGNIZED VALUE']])
			currentBit += 8

		if currentBit < 96:
			self.put(bitData[3][currentBit][0], bitData[3][95][2], self.out_ann,
				[9, ['Segment not used by recognized message types']])
			self.put(bitData[3][currentBit][0], bitData[3][95][2], self.out_ann,
				[12, ['Segment not used by recognized message types']])
		
		while currentBit < 96:
			if self.values[int(currentBit/8)] == 0x00:
				currentBit += 8
			else:
				self.put(bitData[3][currentBit][0], bitData[3][currentBit+7][2], self.out_ann,
					[10, ['Unclaimed byte is nonzero!']])
				currentBit += 8
	
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
		tempCalcedChecksum = self.checksum
		tempReceivedChecksum = self.putValueLSBFirst(bitData, currentBit+80, 8)
		if tempCalcedChecksum == tempReceivedChecksum:
			self.put(bitData[3][currentBit+80][0], bitData[3][currentBit+87][2], self.out_ann,
				[3, ['Checksum, calculated value 0x%02X, valid!' % tempCalcedChecksum]])
		else:
			self.put(bitData[3][currentBit+80][0], bitData[3][currentBit+87][2], self.out_ann,
				[6, ['Checksum, calculated value 0x%02X, invalid!' % tempCalcedChecksum]])

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
		
		if packetType == 0x83:
			self.put(bitData[3][currentBit+1][0], bitData[3][currentBit+8][2], self.out_ann,
				[11, ['Unsure']])
			self.put(bitData[3][currentBit+1][0], bitData[3][currentBit+8][2], self.out_ann,
				[3, ['Serial number?']])

			self.putUnknownByte(bitData, currentBit+10, self.values[3])
			self.putUnknownByte(bitData, currentBit+19, self.values[4])
			self.putUnknownByte(bitData, currentBit+28, self.values[5])
			self.putUnknownByte(bitData, currentBit+37, self.values[6])

			currentBit += 45
		elif packetType == 0xC0:
			self.put(bitData[3][currentBit+1][0], bitData[3][currentBit+8][2], self.out_ann,
				[3, ['Remote capabilities']])

			self.put(bitData[3][currentBit+10][0], bitData[3][currentBit+17][2], self.out_ann,
				[11, ['Unsure']])
			self.put(bitData[3][currentBit+10][0], bitData[3][currentBit+17][2], self.out_ann,
				[9, ['Which block?']])
			if self.values[3] == 0x01:
				self.put(bitData[3][currentBit+10][0], bitData[3][currentBit+17][2], self.out_ann,
					[3, ['First block, LCD capabilities?']])
				
				self.putUnknownByte(bitData, currentBit+19, self.values[4])
				self.putUnknownByte(bitData, currentBit+28, self.values[5])
				self.putUnknownByte(bitData, currentBit+37, self.values[6])
				self.putUnknownByte(bitData, currentBit+46, self.values[7])
				self.putUnknownByte(bitData, currentBit+55, self.values[8])

				self.put(bitData[3][currentBit+64][0], bitData[3][currentBit+71][2], self.out_ann,
					[11, ['Unsure']])
				self.put(bitData[3][currentBit+64][0], bitData[3][currentBit+71][2], self.out_ann,
					[9, ['Pixels tall?']])
				self.put(bitData[3][currentBit+64][0], bitData[3][currentBit+71][2], self.out_ann,
					[3, ['Pixels tall: %d' % self.values[9]]])
				self.put(bitData[3][currentBit+73][0], bitData[3][currentBit+80][2], self.out_ann,
					[11, ['Unsure']])
				self.put(bitData[3][currentBit+73][0], bitData[3][currentBit+80][2], self.out_ann,
					[9, ['Pixels wide?']])
				self.put(bitData[3][currentBit+73][0], bitData[3][currentBit+80][2], self.out_ann,
					[3, ['Pixels wide: %d' % self.values[10]]])
				self.put(bitData[3][currentBit+82][0], bitData[3][currentBit+89][2], self.out_ann,
					[11, ['Unsure']])
				self.put(bitData[3][currentBit+82][0], bitData[3][currentBit+89][2], self.out_ann,
					[9, ['Character sets supported?']])
				currentBit += 90
			elif self.values[3] == 0x02:
				self.put(bitData[3][currentBit+10][0], bitData[3][currentBit+17][2], self.out_ann,
					[3, ['Second block?']])

				self.put(bitData[3][currentBit+19][0], bitData[3][currentBit+26][2], self.out_ann,
					[11, ['Unsure']])
				self.put(bitData[3][currentBit+19][0], bitData[3][currentBit+26][2], self.out_ann,
					[9, ['Characters displayed?']])
				self.put(bitData[3][currentBit+19][0], bitData[3][currentBit+26][2], self.out_ann,
					[3, ['Characters displayed: %d' % self.values[4]]])

				self.putUnknownByte(bitData, currentBit+28, self.values[5])
				self.putUnknownByte(bitData, currentBit+37, self.values[6])
				self.putUnknownByte(bitData, currentBit+46, self.values[7])
				self.putUnknownByte(bitData, currentBit+55, self.values[8])
				self.putUnknownByte(bitData, currentBit+64, self.values[9])
				self.putUnknownByte(bitData, currentBit+73, self.values[10])
				self.putUnknownByte(bitData, currentBit+82, self.values[11])

				currentBit += 90
			elif self.values[3] == 0x05:
				self.put(bitData[3][currentBit+10][0], bitData[3][currentBit+17][2], self.out_ann,
					[3, ['Fifth block?']])
				
				self.putUnknownByte(bitData, currentBit+19, self.values[4])
				self.putUnknownByte(bitData, currentBit+28, self.values[5])
				self.putUnknownByte(bitData, currentBit+37, self.values[6])
				self.putUnknownByte(bitData, currentBit+46, self.values[7])
				self.putUnknownByte(bitData, currentBit+55, self.values[8])
				self.putUnknownByte(bitData, currentBit+64, self.values[9])
				self.putUnknownByte(bitData, currentBit+73, self.values[10])
				self.putUnknownByte(bitData, currentBit+82, self.values[11])

				currentBit += 90
			else:
				self.put(bitData[3][currentBit+10][0], bitData[3][currentBit+17][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
		else:
			self.put(bitData[3][currentBit+1][0], bitData[3][currentBit+8][2], self.out_ann,
					[10, ['UNRECOGNIZED VALUE']])
			currentBit += 9
		
		if currentBit < 106:
			self.put(bitData[3][currentBit][0], bitData[3][105][2], self.out_ann,
				[9, ['Segment not used by recognized message types']])
			self.put(bitData[3][currentBit][0], bitData[3][105][2], self.out_ann,
				[12, ['Segment not used by recognized message types']])
		
		while currentBit < 106:
			if self.values[int(2+((currentBit-16)/9))] == 0x00:
				currentBit += 9
			else:
				self.put(bitData[3][currentBit+1][0], bitData[3][currentBit+8][2], self.out_ann,
					[10, ['Unclaimed byte is nonzero!']])
				currentBit += 9
	
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
				
