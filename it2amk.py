import pyIT
import math
import sys
import re
import subprocess
import os
import operator

class CompileErrorException(Exception):
    pass

class Config:
	flags = {
		'nosmpl' : [False, 'bool'],			# Skip the sample conversion phase
		'addmml' : [[], None],				# List of MML snippets to add
		'game' : ['', 'string'],			# Game title
		'author' : ['', 'string'],			# Author name
		'length' : ['', 'time'],			# SPC length
		'tmult' : [2, 'real'],				# Tempo multiplier
		'vmult' : [1.0, 'real'],			# Volume multiplier
		'chipc' : [1, 'int'],				# Number of SPC chip instances
		'vcurve' : ['accurate', 'string'],	# accurate, linear, x^2
		'panning' : ['accurate', 'string'],	# linear, accurate
		'tspeed' : [False, 'bool'],			# Use txxx for Axx commands
		'legato' : [True, 'bool'],			# Whether or not to apply $F4 $02
		'vcmd' : ['v', 'string'],			# Which volume command to use for the v column
		'mcmd' : ['v', 'string'],			# Which volume command to use for the M effect
		'svcmd' : ['v', 'string'],			# Which volume command to use for global sample volume
		'ivcmd' : ['v', 'string'],			# Which volume command to use for global instrument volume
		'resample' : [1.0, 'real'],			# Constant resample ratio across all samples
		'amplify' : [0.92, 'real'],			# Constant amplify ratio across all samples
		'echo' : ['', 'hex', 8],			# Echo parameters
		'fir' : ['', 'hex', 16],			# Fir parameters
		'master' : ['', 'hex', 4]			# Master level (left and right)
	}
	flag_aliases = {
		'ns' : 'nosmpl',
		'mm' : 'addmml',
		'gm' : 'game',
		'au' : 'author',
		'ln' : 'length',
		't' : 'tmult',
		'vm' : 'vmult',
		'c' : 'chipc',
		'vc' : 'vcurve',
		'p' : 'panning',
		'ts' : 'tspeed',
		'l' : 'legato',
		'v' : 'vcmd',
		'm' : 'mcmd',
		'sv' : 'svcmd',
		'iv' : 'ivcmd',
		'r' : 'resample',
		'a' : 'amplify',
		'e' : 'echo',
		'f' : 'fir',
		'ml' : 'master'
	}
	
	@staticmethod
	def flag(f):
		return Config.flags[f][0]
		
	@staticmethod
	def set_flag(flag, value):
		if flag.startswith('--') and len(flag) >= 3 and flag[2] != '-':
			flag = flag[2:]
	
		try:
			if flag.startswith('-'):
				flag = Config.flag_aliases[flag[1:]]
		
			if Config.flags[flag][1] == 'string':
				Config.flags[flag][0] = value
			elif Config.flags[flag][1] == 'time':
				if re.match('^[0-9]+:[0-9]+$', value):
					Config.flags[flag][0] = value
				else:
					raise ValueError(flag + ' must be in the format m:ss.')
			elif Config.flags[flag][1] == 'hex':
				if re.match('^([0-9]|[A-F]|[a-f])+$', value) and (len(Config.flags[flag]) < 3 or len(value) >= Config.flags[flag][2]):
					Config.flags[flag][0] = value
				elif not re.match('^([0-9]|[A-F]|[a-f])+$', value):
					raise ValueError(flag + ' must be a hexadecimal string.')
				else:
					raise ValueError(flag + ': "' + value + '" is too short.')
			elif Config.flags[flag][1] == 'int':
				try:
					Config.flags[flag][0] = int(value)
				except ValueError:
					raise ValueError(flag + ' must be an integer.')
			elif Config.flags[flag][1] == 'real':
				try:
					Config.flags[flag][0] = float(value)
				except ValueError:
					raise ValueError(flag + ' must be a real number.')
			elif Config.flags[flag][1] == 'bool':
				if value.lower() == 'true':
					Config.flags[flag][0] = True
				elif value.lower() == 'false':
					Config.flags[flag][0] = False
				else:
					raise ValueError(flag + ' must be true or false.')
			else:
				splits = value.split(':', 4)
				Config.flags[flag][0].append([])
				
				Config.flags[flag][0][-1].append(0)
				Config.flags[flag][0][-1].append(1)
				Config.flags[flag][0][-1].append(0)
				Config.flags[flag][0][-1].append(0)
				Config.flags[flag][0][-1].append('')
				
				for i in range(0, len(splits) - 1):
					Config.flags[flag][0][-1][i] = int(splits[i])
				Config.flags[flag][0][-1][-1] = splits[-1]
				
		except KeyError:
			raise ValueError('Flag ' + flag + ' does not exist or is not supported in this version of it2amk.')

	@staticmethod
	def get_module_flags(it):
		flag_text = ''
		interpret = False
		for c in it.Message:
			if c == '`':
				interpret = not interpret
				flag_text = ''.join((flag_text, ' '))
			elif interpret:
				flag_text = ''.join((flag_text, c))
				
		flag_text = flag_text.replace('\r', '').replace('\n', ' ').replace('\t', ' ')
		
		# Replace all spaces in quotes with \s
		flag_text_2 = ''
		quote = False
		for c in flag_text:
			if c == '"':
				quote = not quote
			elif c == ' ' and quote:
				flag_text_2 = ''.join((flag_text_2, '\\s'))
			else:
				flag_text_2 = ''.join((flag_text_2, c))
				
		flags = flag_text_2.split()
		if len(flags) % 2 != 0:
			print('Error: Missing flag argument in module song message.')
			sys.exit(1)
			
		f = 0
		while f < len(flags):
			flag = flags[f].replace('\\s', ' ')
			arg = flags[f + 1].replace('\\s', ' ')
			
			try:
				Config.set_flag(flag, arg)
			except ValueError as e:
				print('Error: ' + str(e))
				sys.exit(1)
			except KeyError as e:
				print('Error: ' + str(e))
				sys.exit(1)
			
			f += 2
			
class EventState:
	def __init__(self):
		self.state_d = { '':None, 'M':None, 'S':0x90, 'X':0x80,
						'E':0x00, 'H':0x00, 'I':0x00, 'J':0x00,
						'Q':0x00, 'R':0x00, 'v':None, '@':None,
						'IV':None, 'SV':None, 'EV':None, 'EX':32, 'EE':None,
						'eflag':False, 'pflag':False, 'H':0x00, 'Hon':False,
						'Z1':None, 
						'a':0x00, 'b':0x00, 'c':0x00, 'd':0x00, 'l':0x00, 'r':0x00,
						'D':0x00, 'N':0x00, 'P':0x00 }
	
class Event:
	def __init__(self, tick, effect, value, visible=True):
		self.tick = tick
		self.effect = effect
		self.value = value
		self.visible = visible
		
class EventTable:
	def __init__(self, module):
		self.events = [[], [], [], [], [], [], [], []]
		self.g_events = []
		self.module = module
		self.states = [EventState(), EventState(), EventState(), EventState(), \
						EventState(), EventState(), EventState(), EventState()]
		self.g_state_d = { 'T': None, 'V': None }
		self.used_samples = set()
		self.sample_dict = {}
		self.ins_dict = {}
		self.ins_list = []
		self.loop_tick = 0
		self.convert()
		
	def get_ins_flags(self, c):
		it_ins = self.states[c].state_d['@']
		return self.get_ins_flags_ins(it_ins)
		
	def get_ins_flags_ins(self, it_ins):
		flags = { 'e':False, 'i':False, 'n':False, 'p':False, 'a':None, 'r':None, 'f':None }
		ins_name = self.module.Instruments[it_ins - 1].InstName + self.module.Instruments[it_ins - 1].Filename
		interpret = False
		current_flag = None
		current_value = ''
		
		for c in ins_name:
			if c == '`':
				interpret = not interpret
			elif interpret:
				if current_flag is not None:
					if current_flag == 'a' or current_flag == 'r':
						current_value += c
						if len(current_value) == 6:
							flags[current_flag] = current_value
							vtype = 'adsr' if current_flag == 'a' else 'release'
							if not re.match('^([0-9]|[A-F]|[a-f])+$', current_value):
								raise CompileErrorException('Instrument ' + str(it_ins) + ': Invalid ' + vtype + ' value "' + current_value + '".')
							current_flag = None
							current_value = ''
					elif current_flag == 'f':
						current_value += c
						if len(current_value) == 2:
							flags[current_flag] = current_value
							if not re.match('^([0-9]|[A-F]|[a-f])+$', current_value):
								raise CompileErrorException('Instrument ' + str(it_ins) + ': Invalid ' + 'fade' + ' value "' + current_value + '".')
							current_flag = None
							current_value = ''
				else:
					if c == 'e':
						flags['e'] = True
					elif c == 'i':
						flags['i'] = True
					elif c == 'n':
						flags['n'] = True
					elif c == 'p':
						flags['p'] = True
					elif c == 'a':
						current_flag = 'a'
					elif c == 'r':
						current_flag = 'r'
					elif c == 'f':
						current_flag = 'f'
						
		return flags
		
	def get_samp_flags(self, it_samp):
		flags = { '@':None, 'r':1.0, 'a':1.0 }
		samp_name = self.module.Samples[it_samp - 1].SampleName + self.module.Samples[it_samp - 1].Filename
		interpret = False
		current_flag = None
		current_value = ''
		
		for cc in range(len(samp_name)):
			c = samp_name[cc]
			if c == '`':
				interpret = not interpret
			elif interpret:
				if current_flag is not None:
					if current_flag == 'a' or current_flag == 'r':
						current_value += c
						if cc >= len(samp_name) - 1 or ((samp_name[cc + 1] < '0' or samp_name[cc + 1] > '9') and samp_name[cc + 1] != '.' and samp_name[cc + 1] != '-'):
							flags[current_flag] = current_value
							vtype = 'amplifier' if current_flag == 'a' else 'resampler'
							if not re.match('^-?([0-9])+(.[0-9]+)?$', current_value):
								raise CompileErrorException('Sample ' + str(it_samp) + ': Invalid ' + vtype + ' value "' + current_value + '".')
							current_flag = None
							current_value = ''
					elif current_flag == '@':
						current_value += c
						if cc >= len(samp_name) - 1 or ((samp_name[cc + 1] < '0' or samp_name[cc + 1] > '9') and samp_name[cc + 1] != '-'):
							flags[current_flag] = current_value
							vtype = '#default sample override'
							if not re.match('^-?([0-9])+$', current_value):
								raise CompileErrorException('Sample ' + str(it_samp) + ': Invalid ' + vtype + ' value "' + current_value + '".')
							current_flag = None
							current_value = ''
				else:
					if c == 'a':
						current_flag = 'a'
					elif c == 'r':
						current_flag = 'r'
					elif c == '@':
						current_flag = '@'
						
		return flags

	def add_init_events(self):
		#self.events[0].append(Event(0, 'V', self.module.GV))
		#self.events[0].append(Event(0, 'T', self.module.IT))
		
		for c in range(0, 8):
			self.events[c].append(Event(0, 'M', self.module.ChannelVols[c]))
			if self.module.ChannelPans[c] % 128 == 100:
				self.events[c].append(Event(0, 'X', 0x80))
				self.events[c].append(Event(0, 'S', 0x91))
			else:
				self.events[c].append(Event(0, 'X', min(self.module.ChannelPans[c] * 4, 0xFF)))
			
	def get_sample(self, ins, note):
		#print(ins, note)
		#print(self.module.Instruments[3].SampleTable)
		sample = self.module.Instruments[ins - 1].SampleTable[note][1] # Not sure if this needs to subtract 1
		#print(sample)
		return sample
		
	def get_default_vol(self, ins, note):
		vol = self.module.Samples[self.get_sample(ins, note) - 1].Vol
		#print(vol)
		return vol
		
	def get_default_pan(self, ins, note):
		pan = self.module.Samples[self.get_sample(ins, note) - 1].DfP
		return pan
		
	def get_note(self, ins, note):
		sample_map = self.module.Instruments[ins].SampleTable
		return sample_map[note][0]
		
	def get_sample_count(self, ins):
		samples = set()
		for i in range(0, 120):
			samples.add(self.module.Instruments[ins][1])
		return len(samples)
			
	def get_row_speed(self, r, speed):
		s = speed
		for c in range(0, 64):
			itnote = r[c]
			if itnote.Effect is not None and itnote.Effect == 1 and itnote.EffectArg != 0x00:
				s = itnote.EffectArg
		return s
		
	def get_row_tempo(self, r, tempo):
		cc = None
		t = tempo
		for c in range(0, 64):
			itnote = r[c]
			if itnote.Effect is not None and itnote.Effect == 20 and itnote.EffectArg >= 0x20:
				t = itnote.EffectArg
				cc = c
		return (cc, t)
		
	def get_row_global_vol(self, r, gvol):
		cc = None
		g = gvol
		for c in range(0, 64):
			itnote = r[c]
			if itnote.Effect is not None and itnote.Effect == 22 and itnote.EffectArg <= 0x80:
				g = itnote.EffectArg
				cc = c
		return (cc, g)
		
	def find_pos_jump(self, r, speed):
		p, row = None, None
		for c in range(0, 64): # Search for B effect (jump to position)
			itnote = r[c]
			if itnote.Effect is not None and itnote.Effect == 2:
				p = itnote.EffectArg
		for c in range(0, 64): # Search for C effect (jump to row (in next position by default))
			itnote = r[c]
			if itnote.Effect is not None and itnote.Effect == 3:
				row = itnote.EffectArg
		if p is not None and row is None:
			row = 0
		return p, row
		
	def handle_loops(self, rr, r, loop_table): # loop_table : 64-list of 2-lists initialized to [[0, 0], [0, 0], ...]
		row_dest = None
		for c in range(0, 64):
			itnote = r[c]
			if itnote.Effect is not None and itnote.Effect == 19 and (itnote.EffectArg >> 4) == 0xB:
				if (itnote.EffectArg & 0xF) == 0x0: # Set loop start for channel
					loop_table[c][0] = rr
				elif loop_table[c][1] == 0: # Set loop counter to value
					loop_table[c][1] = itnote.EffectArg & 0xF
					row_dest = loop_table[c][0]
				elif loop_table[c][1] < 0:
					loop_table[c][1] = 1
					row_dest = loop_table[c][0]
				elif loop_table[c][1] == 1:
					loop_table[c][1] = 0
					loop_table[c][0] = rr + 1
				else:
					loop_table[c][1] -= 1
					row_dest = loop_table[c][0]
		return row_dest
		
	def get_pattern_delay(self, r):
		for c in range(0, 64):
			itnote = r[c]
			if itnote.Effect is not None and itnote.Effect == 19 and (itnote.EffectArg >> 4) == 0xE:
				return itnote.EffectArg & 0xF
		return 0
		
	def add_note(self, r, c, basetick, subtick, speed, value):
		self.states[c].state_d[''] = value
		self.events[c].append(Event(basetick + subtick, '', value))
		
	def add_vol(self, r, c, basetick, subtick, speed, value):
		self.states[c].state_d['v'] = value
		self.events[c].append(Event(basetick + subtick, 'v', value))
		
	def add_instrument(self, r, c, basetick, subtick, speed, value):
		self.states[c].state_d['@'] = value
		self.events[c].append(Event(basetick + subtick, '@', value))
		
		ins_vol = self.module.Instruments[value - 1].GbV
		self.states[c].state_d['IV'] = ins_vol
		self.events[c].append(Event(basetick + subtick, 'IV', ins_vol))
		
		# Get ins flags
		
		flags = self.get_ins_flags(c)
		# Add echo/pmod flags
		#self.events[c].append(Event(basetick + subtick, 'eflags', flags['e'], False))
		
		#self.events[c].append(Event(basetick + subtick, 'pflags', flags['p'], False))
		
		if flags['e'] != self.states[c].state_d['eflag']:
			self.g_events.append(Event(basetick + subtick, 'eflags', (c, flags['e']), False))
		if flags['p'] != self.states[c].state_d['pflag']:
			self.g_events.append(Event(basetick + subtick, 'pflags', (c, flags['p']), False))
		self.states[c].state_d['eflag'] = flags['e']
		self.states[c].state_d['pflag'] = flags['p']
		
		# Lookup sample default volume
		if r[c].Note is None or r[c].Note >= 120:
			vol = self.get_default_vol(value, self.states[c].state_d[''])
			smp_vol = self.module.Samples[self.get_sample(value, self.states[c].state_d['']) - 1].GvL
		else:
			vol = self.get_default_vol(value, r[c].Note)
			smp_vol = self.module.Samples[self.get_sample(value, r[c].Note) - 1].GvL
		self.events[c].append(Event(basetick + subtick, 'v', vol))
		self.states[c].state_d['v'] = vol
		
		self.states[c].state_d['SV'] = smp_vol
		self.events[c].append(Event(basetick + subtick, 'SV', smp_vol))
		
		# Lookup instrument default panning
		dfp = self.module.Instruments[value - 1].DfP
		if dfp < 128:
			self.states[c].state_d['X'] = min(dfp * 4, 0xFF)
		# Lookup sample default panning
		if r[c].Note is None or r[c].Note >= 120:
			dfp = self.get_default_pan(value, self.states[c].state_d[''])
		else:
			dfp = self.get_default_pan(value, r[c].Note)
		if dfp >= 128:
			self.states[c].state_d['X'] = min((dfp & 0x7F) * 4, 0xFF)
			
		self.events[c].append(Event(basetick + subtick, 'X', self.states[c].state_d['X']))
		self.events[c].append(Event(basetick + subtick, 'EX', 32)) # TODO: Figure out pan envelope
		
		lastnote = self.states[c].state_d['']
		if r[c].Note is None and lastnote is not None and lastnote < 120:
			self.add_note(r, c, basetick, subtick, speed, lastnote) # Repeat last note
		
	def add_volume(self, r, c, basetick, subtick, speed, value):
		self.states[c].state_d['v'] = value
		self.events[c].append(Event(basetick + subtick, 'v', value))
		
	def add_mvolume(self, r, c, basetick, subtick, speed, value):
		self.states[c].state_d['M'] = value
		self.events[c].append(Event(basetick + subtick, 'M', value))
		
	def add_panning(self, r, c, basetick, subtick, speed, value):
		self.states[c].state_d['X'] = value
		self.events[c].append(Event(basetick + subtick, 'X', value))
		
	def add_surround(self, r, c, basetick, subtick, speed, value):
		self.states[c].state_d['S'] = value
		self.events[c].append(Event(basetick + subtick, 'S', value))
		
	def add_z1(self, r, c, basetick, subtick, speed, value):
		self.states[c].state_d['Z1'] = value
		self.events[c].append(Event(basetick + subtick, 'Z1', value))
		
	def add_row_events(self, rr, r, basetick, speed, order, iter):
		for c in range(0, 8): # TODO: Ghost channel/NNA support
			if basetick != 0 and iter == 0:
				if rr == 0:
					self.events[c].append(Event(basetick, 'patt', 0)) # mark empty line between patterns
				if rr % self.module.PHilight_major == 0:
					self.events[c].append(Event(basetick, 'bar', 0)) # mark newline for each measure
		
			for m in Config.flag('addmml'):
				if m[0] == order and m[1] - 1 == c and m[2] == rr and m[3] == 0:
					if iter == 0:
						self.events[c].append(Event(basetick, 'mml', m[-1]))
		
			subtick = 0
			cuttick = None
			
			vffade_vol, pffade_vol = 0, 0
			vfade_vol, pfade_vol = 0, 0
			
			vffade_eff, pffade_eff = 0, 0
			vfade_eff, pfade_eff = 0, 0
			
			if r[c].Effect is not None:
				if r[c].Effect == 11: # K effect
					if not self.states[c].state_d['Hon']:
						self.events[c].append(Event(basetick, 'H', self.states[c].state_d['H']))
					self.states[c].state_d['Hon'] = True
					#self.states[c].state_d['H'] = hval
						
				elif r[c].Effect == 19: # S effect
					if (r[c].EffectArg >> 4) == 0xD: # Row delay
						subtick = r[c].EffectArg & 0xF
					elif (r[c].EffectArg >> 4) == 0xC: # Note cut
						if (r[c].EffectArg & 0xF) < speed:
							cuttick = max(r[c].EffectArg & 0xF, 1)
					elif r[c].EffectArg == 0x91 or r[c].EffectArg == 0x90: # Surround On/Off
						if iter == 0:
							self.add_surround(r, c, basetick, subtick, speed, r[c].EffectArg)
				elif r[c].Effect == 13: # M effect
					if iter == 0:
						self.add_mvolume(r, c, basetick, subtick, speed, r[c].EffectArg)
				elif r[c].Effect == 8: # H effect
					if iter == 0:
						hval = self.states[c].state_d['H']
						if r[c].EffectArg & 0x0F != 0:
							hval = (hval & 0xF0) | (r[c].EffectArg & 0x0F)
						if r[c].EffectArg & 0xF0 != 0:
							hval = (hval & 0x0F) | (r[c].EffectArg & 0xF0)
							
						if not self.states[c].state_d['Hon'] or hval != self.states[c].state_d['H']:
							self.events[c].append(Event(basetick, 'H', hval))
						self.states[c].state_d['Hon'] = True
						self.states[c].state_d['H'] = hval
				elif r[c].Effect == 26: # Z effect
					if iter == 0:
						self.add_z1(r, c, basetick, subtick, speed, r[c].EffectArg)
						
			if r[c].Effect is None or (r[c].Effect != 8 and r[c].Effect != 11): # If no vibrato in this row
				if self.states[c].state_d['Hon']:
					self.events[c].append(Event(basetick, 'H', 0x00))
				self.states[c].state_d['Hon'] = False
					
			# This particular loop is only for handling inserted mml.
			# For Fade commands such as axx, use the range(subtick, speed) loop. (They respond to delay)
			for tick in range(1, min(subtick + 1, speed)):
				for m in Config.flag('addmml'):
					if m[0] == order and m[1] - 1 == c and m[2] == rr and m[3] == tick:
						if iter == 0:
							self.events[c].append(Event(basetick + tick, 'mml', m[-1]))
			
			if subtick < speed:
				if r[c].Instrument is not None:
					if iter == 0:
						self.add_instrument(r, c, basetick, subtick, speed, r[c].Instrument)
				if r[c].Volume is not None:
					if r[c].Volume <= 64:
						if iter == 0:
							self.add_volume(r, c, basetick, subtick, speed, r[c].Volume)
					elif r[c].Volume >= 65 and r[c].Volume <= 74: # Fine volume up
						param = r[c].Volume - 65
						if param > 0:
							self.states[c].state_d['a'] = param
							vffade_vol = param
						else:
							vffade_vol = self.states[c].state_d['a']
					elif r[c].Volume >= 75 and r[c].Volume <= 84: # Fine volume down
						param = r[c].Volume - 75
						if param > 0:
							self.states[c].state_d['b'] = param
							vffade_vol = -param
						else:
							vffade_vol = -self.states[c].state_d['b']
					elif r[c].Volume >= 85 and r[c].Volume <= 94: # Volume up
						param = r[c].Volume - 85
						if param > 0:
							self.states[c].state_d['c'] = param
							self.states[c].state_d['D'] = param << 4
							vfade_vol = param
						else:
							vfade_vol = self.states[c].state_d['c']
							self.states[c].state_d['D'] = self.states[c].state_d['c'] << 4
					elif r[c].Volume >= 95 and r[c].Volume <= 104: # Volume down
						param = r[c].Volume - 95
						if param > 0:
							self.states[c].state_d['d'] = param
							self.states[c].state_d['D'] = param
							vfade_vol = -param
						else:
							vfade_vol = -self.states[c].state_d['d']
							self.states[c].state_d['D'] = self.states[c].state_d['d']
					elif r[c].Volume >= 128 and r[c].Volume <= 192: # Panning
						if iter == 0:
							self.add_panning(r, c, basetick, subtick, speed, min((r[c].Volume - 128) * 4, 255))
							
				if r[c].Effect is not None and r[c].Effect == 24: # add X effect AFTER instrument
					if iter == 0:
						self.add_panning(r, c, basetick, subtick, speed, r[c].EffectArg)
						self.add_surround(r, c, basetick, subtick, speed, 0x90)
						
				if r[c].Effect == 4 or r[c].Effect == 11 or r[c].Effect == 12: # D, K, L effect
					d = r[c].EffectArg
					if d == 0x00:
						d = self.states[c].state_d['D']
					self.states[c].state_d['D'] = d
						
					if (d >> 4) == 0x0: # Volume slide down
						param = d & 0xF
						vfade_eff = -param
					elif d & 0xF == 0x0: # Volume slide up
						param = d >> 4
						vfade_eff = param
					if d & 0xF == 0xF: # Fine volume slide up
						param = d >> 4
						vffade_eff = param
					elif (d >> 4) == 0xF: # Fine volume slide down
						param = d & 0xF
						vffade_eff = -param
					
				oldvol = self.states[c].state_d['v']
				if vffade_vol != 0 or vffade_eff != 0 :
					newvol = min(max(oldvol + vffade_vol, 0), 64)
					newvol = min(max(newvol + vffade_eff, 0), 64)
					self.states[c].state_d['v'] = newvol
					self.events[c].append(Event(basetick + subtick, 'v', newvol))
					
				if r[c].Note is not None: # Note must always be added after other effects on same tick
					if iter == 0 or subtick > 0:
						self.add_note(r, c, basetick, subtick, speed, r[c].Note)
						if r[c].Note < 120:
							samp = self.get_sample(self.states[c].state_d['@'], r[c].Note)
							if not self.get_ins_flags_ins(self.states[c].state_d['@'])['n']:
								self.used_samples.add(samp)
								if (self.states[c].state_d['@'], samp) not in self.ins_dict:
									self.ins_dict[(self.states[c].state_d['@'], samp)] = 30 + len(self.ins_dict)
									self.ins_list.append((self.states[c].state_d['@'], samp))
							else:
								if (self.states[c].state_d['@'], 0) not in self.ins_dict: # We use sample 0 to denote noise
									self.ins_dict[(self.states[c].state_d['@'], 0)] = 30 + len(self.ins_dict)
									self.ins_list.append((self.states[c].state_d['@'], 0))
					
				for tick in range(subtick + 1, speed):
					for m in Config.flag('addmml'):
						if m[0] == order and m[1] - 1 == c and m[2] == rr and m[3] == tick:
							self.events[c].append(Event(basetick + tick, 'mml', m[-1]))
						
				for tick in range(subtick, speed): # Handle fade commands + note cut
					# fade commands
					if tick > subtick:
						oldvol = self.states[c].state_d['v']
						if vfade_vol != 0 or vfade_eff != 0:
							newvol = min(max(oldvol + vfade_vol, 0), 64)
							newvol = min(max(newvol + vfade_eff, 0), 64)
							self.states[c].state_d['v'] = newvol
							self.events[c].append(Event(basetick + tick, 'v', newvol))
					
					if cuttick is not None and tick == cuttick:
						self.add_note(r, c, basetick, tick, speed, 254)
						
	def get_sample_tunings(self, unused_samples):
		if not Config.flag('nosmpl'):
			try:
				os.remove('temp/tunings.txt')
			except OSError:
				pass
				
			use_string = ''
				
			for s in range(0, len(self.module.Samples)):
				if s + 1 in self.used_samples:
					use_string += '1'
				else:
					use_string += '0'
					
			arg_list = ['sampconv.exe', sys.argv[1], use_string]
			
			# Add resample and amplify ratios
			for s in range(0, len(self.module.Samples)):
				arg_list.append(str(Config.flag('resample')))
				arg_list.append(str(Config.flag('amplify')))
				
			#print('arg_list', arg_list)
				
			subprocess.call(arg_list)
		
		f = open('temp/tunings.txt', 'r')
		lines = f.readlines()
		f.close()
		
		used_list = sorted(list(self.used_samples))
		sample_dict = {}
		
		default_dict = { 0: '00 SMW @0', 1: '01 SMW @1', 2: '02 SMW @2', 3: '03 SMW @3',
			4: '04 SMW @4', 5: '07 SMW @5', 6: '08 SMW @6', 7: '09 SMW @7',
			8: '05 SMW @8', 9: '0A SMW @9', 10: '0B SMW @10', 11: '01 SMW @1',
			12: '10 SMW @12', 13: '0C SMW @13', 14: '0D SMW @14', 15: '12 SMW @15',
			16: '0C SMW @13', 17: '11 SMW @17', 18: '01 SMW @1', 21: '0F SMW @21',
			22: '06 SMW @22', 23: '06 SMW @22', 24: '0E SMW @29', 25: '0E SMW @29',
			26: '0B SMW @10', 27: '0B SMW @10', 28: '0B SMW @10', 29: '0E SMW @29'
		}
		
		used_index = 0
		
		for line in lines:
			nline = ''
			quote = False
			for c in line:
				if c == '"':
					quote = not quote
				elif quote and c == ' ':
					nline += '\\s'
				elif c != '\n' and c != '\r':
					nline += c
			#print(nline)
			args = nline.split(' ')
			sample_name = args[0].replace('\\s', ' ')
			tuning = args[1][:3] + ' $' + args[1][3:]
			
			flags = self.get_samp_flags(used_list[used_index])
			#print('sflags:', used_list[used_index], '-', sample_name, flags)
			default_prefix = '../default/'
			
			override = flags['@']
			if override is not None:
				if int(override) in default_dict:
					sample_name = default_prefix + default_dict[int(override)] + '.brr'
				else:
					sample_name = default_prefix + '13 SMW Thunder.brr'
			
			sample_dict[used_list[used_index]] = (sample_name, tuning)
			
			used_index += 1
			
		return sample_dict
		
	def fix_global_events(self):
		self.g_events.sort(key=operator.attrgetter('tick'))
			
	def convert(self):
		visited = set()
	
		self.add_init_events()
		speed = self.module.IS
		tempo = self.module.IT
		gvol = self.module.GV
		
		tick = 0
		pos = 0
		start_row = 0
		loop_pos, loop_row = 0, 0
		finished = False
		loop_table = [[0, 0] for i in range(64)]
		
		while pos < len(self.module.Orders):
			o = self.module.Orders[pos]
			if o <= 199:
				p = self.module.Patterns[o]
				
				new_pos, new_row = None, None
				rr = start_row
				while rr < len(p.Rows):
					if (pos, rr) in visited:
						is_loop = False
						for c in range(0, 64):
							if loop_table[c][1] > 0:
								is_loop = True
								break
						if not is_loop:
							loop_pos, loop_row = pos, rr
							finished = True
							break
				
					visited.add((pos, rr))

					r = p.Rows[rr]
					patt_delay = self.get_pattern_delay(r)
					speed = self.get_row_speed(r, speed)
					chan, tempo = self.get_row_tempo(r, tempo)
					
					if self.g_state_d['T'] is None or tempo != self.g_state_d['T']:
						if chan is None:
							chan = 0
						self.events[chan % 8].append(Event(tick, 'T', tempo))
						self.g_state_d['T'] = tempo
						
					chan, gvol = self.get_row_global_vol(r, gvol)
					
					if self.g_state_d['V'] is None or gvol != self.g_state_d['V']:
						if chan is None:
							chan = 0
						self.events[chan % 8].append(Event(tick, 'V', gvol))
						self.g_state_d['V'] = gvol
					
					for l in range(0, patt_delay + 1):
						self.add_row_events(rr, r, tick, speed, o, l)
						tick += speed
						
					new_pos, new_row = self.find_pos_jump(r, speed)
					
					no_newline = False
					loop_row = self.handle_loops(rr, r, loop_table)
					if loop_row is not None:
						new_row = loop_row
						if new_row >= len(p.Rows):
							new_row = 0
							new_pos = pos + 1
						else:
							no_newline = True
							new_pos = pos
					
					if not no_newline and new_pos is not None and new_row is not None and new_row != 0:
						for c in range(0, 8):
							self.events[c].append(Event(tick, 'patt', 0))
							if new_row % self.module.PHilight_major != 0:
								self.events[c].append(Event(tick, 'bar', 0))
					
					if new_pos is not None or new_row is not None:
						break
						
					rr += 1
					
				if finished:
					break
					
				if new_pos is not None:
					pos = new_pos
				else:
					pos += 1
					
				if pos >= len(self.module.Orders) or self.module.Orders[pos] >= 200:
					pos = 0 # TODO: Jump back to first pos in continuous block instead of 0
					
				if new_row is not None:
					if new_row >= len(self.module.Patterns[self.module.Orders[pos]].Rows):
						new_row = 0
					start_row = new_row
				else:
					start_row = 0
			else:
				break
					
		unused_samples = set()
		for s in range(0, len(self.module.Samples)):
			if s + 1 not in self.used_samples:
				unused_samples.add(s + 1)
		#print('Used samples:', self.used_samples)
		#print('Unused samples:', unused_samples)
		#print('Loop position, Loop row: ', (loop_pos, loop_row))
		
		tunings = self.get_sample_tunings(unused_samples)
		self.sample_dict = tunings
		#print(self.sample_dict)
					
		for c in range(0, 8):
			self.events[c].append(Event(tick, 'end', 0))
			
		self.fix_global_events()
			
		# Calculate tick of loop point
		tick = 0
		speed = self.module.IS
		finished = False
		for pos in range(0, len(self.module.Orders)):
			o = self.module.Orders[pos]
			if o <= 199:
				p = self.module.Patterns[o]
				for rr in range(0, len(p.Rows)):
					if loop_pos == pos and loop_row == rr:
						self.loop_tick = tick
						finished = True
						break
				
					r = p.Rows[rr]
					speed = self.get_row_speed(r, speed)
					tick += speed
					
				if finished:
					break
					
		#print('Loop tick:', self.loop_tick)
		
		if self.loop_tick != 0:
			for c in range(0, 8):
				for e in range(0, len(self.events[c])):
					if self.events[c][e].tick >= self.loop_tick:
						self.events[c].insert(e, Event(tick, 'loop', 0))
						break
		
		txt = ''
		for c in range(0, 8):
			txt = ''.join((txt, '#' + str(c) + '\n'))
			for e in self.events[c]:
				txt = ''.join((txt, '    ' + str((e.tick, e.effect, e.value)) + '\n'))
		#file = open('event_table.txt', 'w')
		#file.write(txt)
		#file.close()

class MMLState:
	def __init__(self):
		self.state_d = { 'o':None, 'h':0, 'v':None, 'q':None, \
						'tune':0x00, 'y':(10, 0, 0), 'p':(0, 0, 0), 'trem':(0, 0, 0), \
						'echo':0x00, '@':0, 'dgain':None, 'note':None, \
						'echof':False, 'n':None, 'amp':0x00, 'gain':None }
		self.hstate_d = { '':None, 'M':None, 'S':0x90, 'X':0x80, \
						'E':0x00, 'H':0x00, 'I':0x00, 'J':0x00, \
						'Q':0x00, 'R':0x00, 'v':None, '@':None, \
						'IV':None, 'SV':None, 'EV':None, 'EX':None, 'EE':None, 'H':0x00,
						'Z1':None }
						
class MML:
	def __init__(self, event_table):
		self.txt = ''
		self.event_table = event_table
		self.states = [MMLState(), MMLState(), MMLState(), MMLState(), \
						MMLState(), MMLState(), MMLState(), MMLState()]
		self.g_state = { 'evoll':0, 'evolr':0 }
		self.echo_set = False
		
		self.adsr_rates = [ \
			0, 2048, 1536, 1280, \
			1024, 768, 640, 512, \
			384, 320, 256, 192, \
			160, 128, 96, 80, \
			64, 48, 40, 32, \
			24, 20, 16, 12, \
			10, 8, 6, 5, \
			4, 3, 2, 1 \
		]

		self.sus_levels = [ 0x100, 0x200, 0x300, 0x400, 0x500, 0x600, 0x700, 0x800 ]
		
		self.ds_cache = {}
		self.sr_cache = {}
		self.dsr_cache = {}
		
		self.add_amk_header()
		self.add_spc_info()
		self.add_sample_info()
		self.add_ins_info()
		self.add_init_info()
		
		self.convert()
		
	def init_adsr_caches(self, tempo):
		for d in range(0, 8):
			for s in range(0, 8):
				self.ds_cache[(d, s)] = len(self.calc_decay_table(d, s, tempo))
				
		for s in range(0, 8):
			for r in range(0, 32):
				self.sr_cache[(s, r)] = len(self.calc_release_table(s, r, tempo))
				
		for d in range(0, 8):
			for s in range(0, 8):
				for r in range(0, 32):
					self.dsr_cache[(d, s, r)] = self.ds_cache[(d, s)] + self.sr_cache[(s, r)] - 1
		
	def add_amk_header(self):
		self.txt = ''.join(('#amk 2\n\n', self.txt))
		
	def add_spc_info(self):
		spc_text = '#SPC\n{\n'
		add_spc_header = False
		
		if self.event_table.module.SongName != '':
			add_spc_header = True
			title = self.event_table.module.SongName.replace('\r', '').replace('\n', ' ').replace('"', "'")
			spc_text += '    #title   "' + title + '"\n'
		if Config.flag('game') != '':
			add_spc_header = True
			spc_text += '    #game    "' + Config.flag('game').replace('\r', '').replace('\n', ' ').replace('"', "'") + '"\n'
		if Config.flag('author') != '':
			add_spc_header = True
			spc_text += '    #author  "' + Config.flag('author').replace('\r', '').replace('\n', ' ').replace('"', "'") + '"\n'
		if Config.flag('length') != '':
			add_spc_header = True
			spc_text += '    #length  "' + Config.flag('length').replace('\r', '').replace('\n', ' ').replace('"', "'") + '"\n'
		if self.event_table.module.Message != '':
			add_spc_header = True
			msg = self.event_table.module.Message.replace('\r', '').replace('\n', ' ').replace('"', "'")
			msg2 = ''
			interpret = False
			for c in msg:
				if c == '`':
					interpret = not interpret
				elif not interpret:
					msg2 = ''.join((msg2, c))
			spc_text += '    #comment "' + msg2.strip() + '"\n'
			
		spc_text += '}\n\n'
		
		if add_spc_header:
			self.txt = ''.join((self.txt, spc_text))
			
	def add_sample_info(self):
		path = sys.argv[1].replace('\\', '/').split('/')[-1].split('.')[0]
		sample_text = '#path ' + '"' + path + '"' + '\n\n' + '#samples\n{\n'
		add_sample_header = False
		
		for k in self.event_table.sample_dict:
			add_sample_header = True
			sample_name = self.event_table.sample_dict[k][0]
			sample_text += '    ' + '"' + sample_name + '"' + '\n'
			
		sample_text += '}\n\n'
		
		if add_sample_header:
			self.txt = ''.join((self.txt, sample_text))
			
	def calc_env_table(self, env):
		envtable, loop_end = [], None
		tick = 0
		current_node_i = -1
		while tick < env.Nodes[env.numNodePoints - 1].tick:
			if tick == env.Nodes[current_node_i + 1].tick:
				current_node_i += 1
				if env.SusloopOn and env.SLE == current_node_i:
					loop_end = env.Nodes[current_node_i].tick
				envtable.append(env.Nodes[current_node_i].y_val * 4)
			else:
				dist = env.Nodes[current_node_i + 1].tick - env.Nodes[current_node_i].tick
				if dist > 0:
					p = (tick - env.Nodes[current_node_i].tick) / dist
					value = p * env.Nodes[current_node_i + 1].y_val + (1 - p) * env.Nodes[current_node_i].y_val
					envtable.append(int(round(value * 4)))
			tick += 1
		envtable.append(env.Nodes[env.numNodePoints - 1].y_val * 4)
		if env.SusloopOn and env.SLE == env.numNodePoints - 1:
			loop_end = env.Nodes[env.numNodePoints - 1].tick
		return envtable, loop_end
			
	def calc_attack(self, envtable, loop_end, tempo):
		peak, peak_index = -1, -1
		
		i = 0
		while i < len(envtable):
			if envtable[i] > peak:
				peak = envtable[i]
				peak_index = i
			i += 1
			
		#TODO: Normalize envelope to peak value and reduce ins volume based on peak value
		
		tick_length = peak_index * (1 - envtable[0] / 256)
		ticks_per_second = float(tempo) * 24 / 60.0
		attack_length = 32000.0 / float(ticks_per_second) * tick_length
		interval = attack_length / 64
		
		# Find most similar rate
		interval2, rate, diff = 2048, 1, 4096
		for i in range(1, len(self.adsr_rates)):
			r = self.adsr_rates[i]
			if abs(interval - r) < diff:
				diff = abs(interval - r)
				interval2 = r
				rate = i
				
		attack = (rate - 1) / 2
		return (int(attack) if peak_index > 0 else None), peak_index
		
	def calc_decay_table(self, d, s, tempo):
		decay_table = []
		
		ticks_per_second = float(tempo) * 24 / 60.0
		level = 0x800
		interval = self.adsr_rates[2*d + 16]
		counter = 0
		tick_counter = 0
		last_tick_counter = 0
		
		decay_table.append(level / 8)
		
		#print('d, s =', (d, s))

		#print('S=',s)
		while level > self.sus_levels[s]:
			counter += interval
			tick_counter = int(counter * float(ticks_per_second) / 32000.0)
			if tick_counter > last_tick_counter:
				last_tick_counter = tick_counter
				decay_table.append(level / 8)
			level -= ((level - 1) >> 8) + 1
			
		decay_table.append(self.sus_levels[s] / 8)
		
		#print('\td, s, decay_table = ', (d, s, decay_table))
		
		return decay_table
		
	def calc_release_table(self, s, r, tempo):
		if r == 0:
			return [self.sus_levels[s]] * 65536
	
		release_table = []
		
		ticks_per_second = float(tempo) * 24 / 60.0
		level = self.sus_levels[s]
		interval = self.adsr_rates[r]
		counter = 0
		tick_counter = 0
		last_tick_counter = 0
		
		release_table.append(level / 8)
		
		while level > 0:
			counter += interval
			tick_counter = int(counter * float(ticks_per_second) / 32000.0)
			if tick_counter > last_tick_counter:
				last_tick_counter = tick_counter
				release_table.append(level / 8)
			level -= ((level - 1) >> 8) + 1
			
		release_table.append(0)
		
		return release_table
		
	def env_diff(self, envtable, adsrtable, itenv_start, itenv_end, tempo):
		tick_length = 1
		ticks_per_second = float(tempo) * 24 / 60.0
		samps_per_tick = 32000.0 / float(ticks_per_second) * tick_length
		
		s, i = 0, itenv_start
		total_diff = 0
		# while s < len(adsrtable) and i < len(envtable):
			# adsr_lvl = adsrtable[int(s)]
			# itenv_lvl = envtable[i]
			
			# total_diff += pow(float(adsr_lvl)/256.0 - float(itenv_lvl)/256.0, 2)
			
			# i += 1
			# s += samps_per_tick
			
		while i <= itenv_end:
			adsr_lvl = adsrtable[min(s, len(adsrtable) - 1)]
			itenv_lvl = envtable[min(i, len(envtable) - 1)]
			
			total_diff += pow(float(adsr_lvl)/256.0 - float(itenv_lvl)/256.0, 2)
			
			s += 1
			i += 1
			
		return total_diff
		
	def calc_dsr(self, envtable, loop_end, d_start, tempo):
		level = 0
		if loop_end is None and envtable[-1] > 0:
			level = envtable[-1]
		elif loop_end is not None and envtable[min(loop_end, len(envtable) - 1)] > 0:
			level = envtable[min(loop_end, len(envtable) - 1)]
			
		if level > 0: # Release is infinite, easier calculation
			the_end = loop_end if loop_end is not None else len(envtable) - 1
			d, s, rr = 0x7, 0x7, None
		
			if level <= 32: # Always lowest sustain
				diff, d, s = 1000000, 0, 0
				for dd in range(0, 8):
					envdiff = self.env_diff(envtable, self.calc_decay_table(dd, 0, tempo), d_start, the_end, tempo)
					if envdiff < diff:
						diff = envdiff
						d = dd
			else: # Guess the 2 sus values that level is between
				diff, d, s = 1000000, 0, 0
				for dd in range(0, 8):
					#print('level =', level)
					for ss in range(min(int(level/32), 7), min(int(level/32) + 1, 8)):
						envdiff = self.env_diff(envtable, self.calc_decay_table(dd, ss, tempo), d_start, the_end, tempo)
						if envdiff < diff:
							diff = envdiff
							d = dd
							s = ss
						
			if the_end != len(envtable) - 1:
				diff, rr = 1000000, None
				for rrr in range(0, 32):
					envdiff = self.env_diff(envtable, self.calc_release_table(s, rrr, tempo), loop_end, len(envtable) - 1, tempo)
					if envdiff < diff:
						diff = envdiff
						rr = rrr
							
			return d, s, 0x0, rr
		else: # Release is finite. Harder calculation
			the_end = loop_end if loop_end is not None else len(envtable) - 1
			length = the_end + 1 - d_start
			tolerance = 0.9
			min_length = length * tolerance
			max_length = length / tolerance
			
			candidates = []
			d, s, r = 0, 0, 0
			smallest, largest = 1000000, 0
			smallest_dsr, largest_dsr = (0, 0, 0), (0, 0, 0)
			
			# Find candidate values to compare similarity to
			for dd in range(0, 8):
				for ss in range(0, 8):
					for rr in range(0, 32):
						env_length = self.dsr_cache[(dd, ss, rr)]
						if env_length >= min_length and env_length <= max_length:
							candidates.append((dd, ss, rr))
						elif env_length < smallest:
							smallest = env_length
							smallest_dsr = (dd, ss, rr)
						elif env_length > largest:
							largest = env_length
							largest_dsr = (dd, ss, rr)
							
			# If no candidates, determine whether too short or too long and pick the correct envelope
			if len(candidates) == 0:
				if max_length > largest:
					return largest_dsr[0], largest_dsr[1], largest_dsr[2], None
				elif min_length < smallest:
					return smallest_dsr[0], smallest_dsr[1], smallest_dsr[2], None
							
			# Calculate similarities of all candidate envelopes
			diff = 1000000
			for (dd, ss, rr) in candidates:
				envdiff = self.env_diff(envtable, self.calc_decay_table(dd, ss, tempo)[:-1] + self.calc_release_table(ss, rr, tempo), d_start, the_end, tempo)
				if envdiff < diff:
					diff = envdiff
					d, s, r = dd, ss, rr
			
			return d, s, r, None
			
	def add_ins_info(self):
		ins_text = '#instruments\n{\n'
		
		#print(self.event_table.ins_dict)
		#print(self.event_table.ins_list)
		
		tempo = self.event_table.module.IT
		self.init_adsr_caches(tempo)
		
		for i in self.event_table.ins_list:
			ins = i[0]
			samp_name, samp_tuning = '', ''
			
			if i[1] > 0:
				samp_name = self.event_table.sample_dict[i[1]][0]
				samp_tuning = self.event_table.sample_dict[i[1]][1]
			else: # if sample 0 (noise), grab first sample in sample dict
				s = None
				for k in self.event_table.sample_dict:
					s = k
					break
				samp_name = self.event_table.sample_dict[s][0]
				samp_tuning = self.event_table.sample_dict[s][1]
			
			flags = self.event_table.get_ins_flags_ins(ins)
			flags_a = flags['a']
			adsr_gain = ''
			
			if flags_a is None:
				if not self.event_table.module.Instruments[ins - 1].volEnv.IsOn:
					flags_a = '00007F'
				else:
					a, d, s, r = 0xF, 0x7, 0x7, 0x0
					envtable, loop_end = self.calc_env_table(self.event_table.module.Instruments[ins - 1].volEnv)
					#print('ins', ins, 'envtable:', envtable)
					a, d_start = self.calc_attack(envtable, loop_end, tempo)
					d, s, r, rr = self.calc_dsr(envtable, loop_end, d_start, tempo)
					#print('d, s, r, rr =', (d, s, r, rr))
					
					if a is None and d == 0x7 and s == 0x7 and r == 0x0:
						flags_a = '00007F'
					else:
						if a is None:
							a = 0xF
						da = hex(d + 0x8)[2:].upper() + hex(a)[2:].upper()
						sr = hex(s * 0x20 + r)[2:].upper()
						flags_a = da + sr + '7F'
						
					if rr is not None and flags['r'] is None: # Override release flag
						flags_r = flags_a[:2] + hex(s * 0x20 + rr)[2:].upper() + '7F'
						#print('FLAGS_R', flags_r)
						self.event_table.module.Instruments[ins - 1].InstName = '`r' + flags_r + '`' + self.event_table.module.Instruments[ins - 1].InstName
						# ^ this is hacky as fuck but hey it works!

			da = '$' + flags_a[:2].upper()
			sr = '$' + flags_a[2:4].upper()
			ga = '$' + flags_a[4:6].upper()
			adsr_gain = da + ' ' + sr + ' ' + ga
				
			ins_text += '    ' + ('"' + samp_name + '"').ljust(32) + ' ' + adsr_gain + ' ' + samp_tuning + (' ; noise' if i[1] == 0 else '') + '\n'
		
		ins_text += '}\n\n'
		self.txt = ''.join((self.txt, ins_text))
		
	def add_init_info(self):
		init_text = ''
		
		init_text += 'w' + str(int(round(255 * math.sqrt(self.event_table.module.GV/128.0)))) + ' '
		init_text += 't' + str(int(math.ceil(self.event_table.module.IT * 0.4096 * Config.flag('tmult')/2))) + '\n\n'
		
		if Config.flag('echo') != '':
			self.g_state['evoll'] = int(Config.flag('echo')[4:6], 16)
			self.g_state['evolr'] = int(Config.flag('echo')[6:8], 16)
			
			init_text += '$EF $00 $' + Config.flag('echo')[4:6].upper() + ' $' + Config.flag('echo')[6:8].upper() + '\n'
			init_text += '$F1 $' + Config.flag('echo')[0:2].upper() + ' $' + Config.flag('echo')[2:4].upper() + ' $01\n\n'
		if Config.flag('fir') != '':
			init_text += '$F5'
			for i in range(0, 8):
				init_text += ' $' + Config.flag('fir')[2*i : 2*i + 2].upper()
			init_text += '\n\n'
		if Config.flag('master') != '':
			init_text += '$F6 $0C $' + Config.flag('master')[0:2].upper() + '\n'
			init_text += '$F6 $1C $' + Config.flag('master')[2:4].upper() + '\n\n'
		if Config.flag('legato'):
			init_text += ('$F4 $02\n\n')
		
		if init_text != '':
			if self.event_table.loop_tick == 0:
				self.txt = ''.join((self.txt, init_text + '/\n\n'))
			else:
				self.txt = ''.join((self.txt, init_text))
		
	def append(self, string, space=False):
		if not space:
			self.txt = ''.join((self.txt, string))
		elif self.txt[-1] != ' ':
			self.txt = ''.join((self.txt, ' ' + string + ' '))
		else:
			self.txt = ''.join((self.txt, string + ' '))
			
	def set_prenote(self, c, noteval, it_tick, use_ins=True):
		# Then, local commands. Do instrument
		if use_ins:
			self.set_mml_ins(c, self.calc_ins(c, noteval), it_tick)
		# Set noise if applicable
		if noteval is not None and noteval < 120 and self.states[c].hstate_d['@'] is not None and noteval is not None and self.event_table.get_ins_flags_ins(self.states[c].hstate_d['@'])['n']:
			noise = noteval % 32
			self.set_mml_n(c, noise)
		# calculate panning, then calculate volume based on volume normalizer from panning
		y, norm = self.calc_y(c, noteval)
		v, amp = self.calc_v(c, norm)
		# v next
		self.set_mml_v(c, v)
		# amp next
		self.set_mml_amp(c, amp)
		# y next
		self.set_mml_y(c, y)
		# vibrato
		self.set_mml_p(c, self.calc_p(c))
		
		# Now ~special commands~
		# Z1 = gain
		self.set_mml_gain(c, self.states[c].hstate_d['Z1'])
		
	def set_note(self, c, effect, value, ticklen):
		if value < 120:
			it_ins = self.states[c].hstate_d['@']
			value = self.event_table.module.Instruments[it_ins - 1].SampleTable[value][0]
	
		notetable = ['c', 'c+', 'd', 'd+', 'e', 'f', 'f+', 'g', 'g+', 'a', 'a+', 'b']
		
		last_octave = self.states[c].state_d['o']
		octave = None
		if self.event_table.get_ins_flags_ins(self.states[c].hstate_d['@'])['n']:
			octave = 4
		else:
			octave = int(value / 12) - 1
		
		#if octave >= 1 and octave < 7:
		if value >= 24 and value < 94:
			self.states[c].state_d['o'] = octave
			
			if last_octave is None:
				self.append('o' + str(octave), True)
			elif octave > last_octave:
				self.append('>' * (octave - last_octave), True)
			elif octave < last_octave:
				self.append('<' * (last_octave - octave), True)
				
			if self.event_table.get_ins_flags_ins(self.states[c].hstate_d['@'])['n']:
				self.append('c' + self.tick_str(c, ticklen))
			else:
				self.append(notetable[value % 12] + self.tick_str(c, ticklen))
			self.states[c].state_d['note'] = notetable[value % 12]
		else:
			self.append('r' + self.tick_str(c, ticklen))
			
	def set_mml_ins(self, c, value, it_tick):
		if value is None:
			return
		if self.states[c].state_d['@'] is None or value != self.states[c].state_d['@']:
			self.states[c].state_d['@'] = value
			self.append('@' + str(value), True)
			self.states[c].state_d['n'] = None
			flags = self.event_table.get_ins_flags_ins(self.states[c].hstate_d['@'])
			
			if self.states[c].state_d['echof'] != flags['e']:
				self.append('$F4 $03', True)
				self.states[c].state_d['echof'] = flags['e']
				
			pmod_chan = self.get_pmod_chan(it_tick)
				
			if pmod_chan is not None and pmod_chan == c:
				pmod_flags = self.get_pmod_flags(it_tick)
				self.append('$FA $00 $' + hex(pmod_flags)[2:].upper().zfill(2), True)
				
	def set_mml_n(self, c, value):
		if value is None:
			return
		if self.states[c].state_d['n'] is None or value != self.states[c].state_d['n']:
			self.states[c].state_d['n'] = value
			self.append('n' + hex(value)[2:].upper(), True)
			
	def set_mml_p(self, c, value):
		if value is None:
			return
		if self.states[c].state_d['p'] is None or value != self.states[c].state_d['p']:
			self.states[c].state_d['p'] = value
			if value[1] == 0 or value[2] == 0:
				self.append('$DF', True)
			else:
				self.append('p' + str(value[0]) + ',' + str(value[1]) + ',' + str(value[2]), True)
			
	def set_mml_t(self, c, value):
		if value is None:
			return
		self.append('t' + str(value), True)
		
	def set_mml_w(self, c, value):
		if value is None:
			return
		self.append('w' + str(value), True)
			
	def set_mml_v(self, c, value):
		if value is None:
			return
		if self.states[c].state_d['v'] is None or value != self.states[c].state_d['v']:
			self.states[c].state_d['v'] = value
			self.append('v' + str(value), True)
			
	def set_mml_amp(self, c, value):
		if value is None:
			return
		if self.states[c].state_d['amp'] is None or value != self.states[c].state_d['amp']:
			self.states[c].state_d['amp'] = value
			self.append('$FA $03 $' + hex(value)[2:].upper().zfill(2), True)
			
	def set_mml_gain(self, c, value):
		if value is None:
			return
		if self.states[c].state_d['gain'] is None or value != self.states[c].state_d['gain']:
			self.states[c].state_d['gain'] = value
			self.append('$FA $01 $' + hex(value)[2:].upper().zfill(2), True)
		
	def set_mml_y(self, c, value):
		if value is None:
			return
		if self.states[c].state_d['y'] is None or value != self.states[c].state_d['y']:
			self.states[c].state_d['y'] = value
			self.append('y' + str(value[0]) + ',' + str(value[1]) + ',' + str(value[2]), True)
		
	def calc_ins(self, c, noteval):
		it_ins = self.states[c].hstate_d['@']
		
		if it_ins is None:
			return None
			
		if self.event_table.get_ins_flags_ins(it_ins)['n']:
			mml_ins = self.event_table.ins_dict[(it_ins, 0)]
			return mml_ins
		else:
			samp = self.event_table.module.Instruments[it_ins - 1].SampleTable[noteval][1]
			mml_ins = self.event_table.ins_dict[(it_ins, samp)]
			return mml_ins
			
	def calc_p(self, c):
		delay, freq, amp = 0, 0, 0
		it_h = self.states[c].hstate_d['H']
		#if it_h != 0x00:
		#	print('IT_H', it_h)
		it_hf = it_h >> 4
		it_ha = it_h & 0x0F
		if it_hf > 0:
			freq = max(min(int(round(256 / ((64 / it_hf) * Config.flag('tmult')))), 255), 0)
		amp = it_ha * 15
		#if it_h != 0x00:
		#	print('DJGFKDHG', (delay, freq, amp))
		return (delay, freq, amp)
		
	def calc_v(self, c, norm):
		#print('NORM =', norm)
	
		# For now assume all volumes feed into v and nothing into q
		it_v = self.states[c].hstate_d['v']
		it_m = self.states[c].hstate_d['M']
		it_iv = self.states[c].hstate_d['IV']
		it_sv = self.states[c].hstate_d['SV']
		
		if it_v is None or it_m is None or it_iv is None or it_sv is None:
			return None, None
		
		linear_v = int(round(255 * norm * Config.flag('vmult') * (it_v/64.0) * (it_m/64.0) * (it_iv/128.0) * (it_sv/64.0)))
		mml_v = self.find_v(min(linear_v, 255))
		amp = 0x00
		if linear_v > 255:
			amp = round(((linear_v / 255) - 1) * 0xFF)
		return mml_v, min(amp, 0xFF)
		
	def calc_y(self, c, noteval):
		it_x = self.states[c].hstate_d['X']
		it_ex = self.states[c].hstate_d['EX']
		it_s = self.states[c].hstate_d['S']
		it_ins = self.states[c].hstate_d['@']

		pps_offset = 0
		
		if it_ins is not None:
			pps = self.event_table.module.Instruments[it_ins - 1].PPS
			ppc = self.event_table.module.Instruments[it_ins - 1].PPC
			pps = pps if pps < 128 else pps - 256
			
			if noteval is not None and noteval < 120:
				pps_offset = pps * (noteval - ppc)
		
		if it_x is None or it_ex is None:
			return None, 1
			
		it_pan = (0xFF - min(max(it_x + 4 * (it_ex - 32) + pps_offset, 0), 0xFF))
		base_pan = None
		if Config.flag('panning') == 'linear':
			base_pan = int(round(it_pan * 20.0/255.0))
		elif Config.flag('panning') == 'accurate':
			smw_pan_tbl = [0x00, 0x01, 0x03, 0x07, 0x0D, 0x15, 0x1E, 0x29, 0x34, 0x42,
			               0x51, 0x5E, 0x67, 0x6E, 0x73, 0x77, 0x7A, 0x7C, 0x7D, 0x7E, 0x7F]
			lvol = max(it_pan, 1) - 0x01
			rvol = 0xFF - max(it_pan, 1)
			
			diff, basepan, rnorm = 1000000, 1.0, None
			for p in range(len(smw_pan_tbl)):
				plvol = smw_pan_tbl[p]
				prvol = smw_pan_tbl[20 - p]
				sum = plvol + prvol
				norm = 254.0 / sum
				
				plvol *= norm
				prvol *= norm
				
				tdiff = abs(plvol - lvol) + abs(prvol - rvol)
				
				if tdiff < diff:
					base_pan = p
					diff = tdiff
					rnorm = norm
					
			#print('RNORM =', rnorm)
			
		# TODO: Factor in pan-per-note and random pan variation
		
		flags = self.event_table.get_ins_flags_ins(it_ins)
		
		if it_s is None or it_s != 0x91:
			return (base_pan, 0, 0) if not flags['i'] else (base_pan, 1, 1), rnorm / 2.0
		else:
			return (10, 1, 0) if not flags['i'] else (10, 0, 1), 1
		
	def find_v(self, level):
		if level == 0:
			return 0
	
		mindiff = 256
		minval = -1
		
		for v in range(0, 256):
			vv = (v * 0xFF) >> 8
			vv = (vv * vv) >> 8
			vv = (vv * 0x51) >> 8
			vv = (vv * 0xFC) >> 8
			l = vv * 0xFF / 0x4D
			
			if abs(l - level) <= mindiff:
				mindiff = abs(l - level)
				minval = v

		return minval
		
	def set_instrument(self, c, effect, value, ticklen):
		self.states[c].hstate_d['@'] = value
			
	def set_v(self, c, effect, value, ticklen):
		self.states[c].hstate_d['v'] = value
		
	def set_m(self, c, effect, value, ticklen):
		self.states[c].hstate_d['M'] = value
		
	def set_iv(self, c, effect, value, ticklen):
		self.states[c].hstate_d['IV'] = value
		
	def get_echo_flags(self, it_tick):
		echo_flags = [0 for x in range(8)]
		e = 0
		while e < len(self.event_table.g_events) and self.event_table.g_events[e].tick < it_tick:
			if self.event_table.g_events[e].effect == 'eflags':
				chan = self.event_table.g_events[e].value[0]
				value = self.event_table.g_events[e].value[1]
				echo_flags[chan] = value
			e += 1
			
		echo_hex = 0x00
		for c in range(8):
			if echo_flags[c]:
				echo_hex |= 1 << c
				
		return echo_hex
		
	def get_pmod_flags(self, it_tick):
		pmod_flags = [0 for x in range(8)]
		e = 0
		while e < len(self.event_table.g_events) and self.event_table.g_events[e].tick <= it_tick:
			if self.event_table.g_events[e].effect == 'pflags':
				chan = self.event_table.g_events[e].value[0]
				value = self.event_table.g_events[e].value[1]
				pmod_flags[chan] = value
			e += 1
			
		pmod_hex = 0x00
		for c in range(8):
			if pmod_flags[c]:
				pmod_hex |= 1 << c
				
		return pmod_hex
		
	def get_pmod_chan(self, it_tick):
		chan = None
		e = 0
		while e < len(self.event_table.g_events) and self.event_table.g_events[e].tick < it_tick:
			e += 1
		while e < len(self.event_table.g_events) and self.event_table.g_events[e].tick == it_tick:
			if self.event_table.g_events[e].effect == 'pflags':
				chan = self.event_table.g_events[e].value[0]
			e += 1
		return chan
		
	def initialize_echo(self, c, it_tick):
		echo_flags = 0x00
		flags_str = hex(self.get_echo_flags(it_tick))[2:].zfill(2).upper()
		evoll_str = hex(self.g_state['evoll'])[2:].zfill(2).upper()
		evolr_str = hex(self.g_state['evolr'])[2:].zfill(2).upper()
		self.append('$EF $' + flags_str + ' $' + evoll_str + ' $' + evolr_str, True)
		self.echo_set = True
		
	def initialize_pmod(self, c, it_tick):
		pmod_flags = self.get_pmod_flags(it_tick)
		self.append('$FA $00 $' + hex(pmod_flags)[2:].upper().zfill(2), True)
		
	def set_mml_cmd(self, c, effect, value, ticklen, ticklen_max, it_tick):
		#ticklen = int(Config.flag('tmult') * ticklen)
		ret = ''
	
		if effect == 'patt' or effect == 'bar':
			ret += '\n    '
			if effect == 'bar' and self.states[c].state_d['o'] is not None:
				ret += 'o' + str(self.states[c].state_d['o']) + ' '
		elif effect == 'loop':
			self.append('/', True)
			if c == 0:
				self.initialize_echo(c, it_tick)
				self.initialize_pmod(c, it_tick)
			self.states[c].state_d['@'] = None
			self.states[c].state_d['v'] = None
			self.states[c].state_d['y'] = None
			self.set_prenote(c, value, it_tick) # Re-init all non-note commands
		elif self.event_table.loop_tick == 0 and not self.echo_set:
			if c == 0:
				self.initialize_echo(c, it_tick)
			
		if effect == '': # Note
			if value < 120:
				self.set_prenote(c, value, it_tick) # Determine all non-note commands
				self.set_note(c, effect, value, ticklen)
			elif value == 255: # Note off
				self.set_prenote(c, value, it_tick, False)
				#self.append('%R' + str(self.states[c].hstate_d['@']), True) # Custom release macro
				#self.append('^' + self.tick_str(ticklen))
				flags = self.event_table.get_ins_flags_ins(self.states[c].hstate_d['@'])
				if flags['r'] is None:
					self.append('r' + self.tick_str(c, ticklen))
				else:
					self.states[c].state_d['@'] = None # Force redef of instrument next note to reset instrument adsr/gain
					self.states[c].state_d['n'] = None
					if int(flags['r'][:2], 16) < 0x80:
						self.append('$FA $01 $' + flags['r'][4:6], True)
					else:
						self.append('$ED $' + hex(int(flags['r'][:2], 16) - 0x80)[2:].zfill(2).upper() + ' $' + flags['r'][2:4], True)
					self.append('^' + self.tick_str(c, ticklen))
			elif value == 254: # Note cut
				self.set_prenote(c, value, it_tick, False)
				self.append('r' + self.tick_str(c, ticklen))
				self.states[c].state_d['note'] = 'r'
			else: # Note fade (TODO: volume fade shit)
				self.set_prenote(c, value, it_tick, False)
				ins = self.states[c].hstate_d['@']
				flags = self.event_table.get_ins_flags_ins(ins)
				
				if flags['f'] is None:
					fade = self.event_table.module.Instruments[ins - 1].FadeOut
					ticks = int(round((1024 / fade) * Config.flag('tmult')))
					#print('TICKLENS:', ticklen, ticklen_max)
					if ticks > ticklen_max:
						fadelevel = int(round(self.states[c].state_d['v'] * (1 - ticklen_max / ticks) + 0x10 * (ticklen_max / ticks)))
						ticks = ticklen_max
					else:
						fadelevel = 0x10
					self.states[c].state_d['v'] = fadelevel
					self.append('$E8 $' + hex(ticks)[2:].upper().zfill(2) + ' $' + hex(fadelevel)[2:].upper().zfill(2), True)
				else:
					fade = 0x80 + (int(flags['f'][:2], 16) & 0x1F)
					self.append('$FA $01 $' + hex(fade)[2:].upper().zfill(2), True)
					self.states[c].state_d['@'] = None
					self.states[c].state_d['n'] = None
					
				self.append('^' + self.tick_str(c, ticklen))
		elif effect == '@':
			self.states[c].hstate_d['@'] = value
		elif effect == 'v':
			self.states[c].hstate_d['v'] = value
		elif effect == 'M':
			self.states[c].hstate_d['M'] = value
		elif effect == 'IV':
			self.states[c].hstate_d['IV'] = value
		elif effect == 'SV':
			self.states[c].hstate_d['SV'] = value
		elif effect == 'X':
			self.states[c].hstate_d['X'] = value
		elif effect == 'EX':
			self.states[c].hstate_d['EX'] = value
		elif effect == 'S':
			self.states[c].hstate_d['S'] = value
		elif effect == 'H':
			self.states[c].hstate_d['H'] = value
		elif effect == 'Z1':
			self.states[c].hstate_d['Z1'] = value
			
		if effect != '':
			if effect == 'T':
				self.append('t' + str(int(math.ceil(value * 0.4096 * Config.flag('tmult')/2))), True)
			elif effect == 'V':
				self.append('w' + str(int(round(255 * math.sqrt(value/128.0)))), True)
			elif effect == 'mml':
				self.append(value.split(';', 1)[0], True)
		
			if ticklen > 0: # Default: just add a tie
				if self.states[c].state_d['note'] is None:
					self.set_prenote(c, None, it_tick, False)
					self.append(ret + 'r' + self.tick_str(c, ticklen))
					self.states[c].state_d['note'] = 'r'
				else:
					self.set_prenote(c, None, it_tick, False)
					self.append(ret + '^' + self.tick_str(c, ticklen))
			else:
				self.append(ret)
				
	def tick_str(self, c, ticklen):
		txt = ''
		while ticklen > 127:
			ticklen -= 127
			txt += '=127^'
		if self.states[c].state_d['n'] is not None:
			#txt += '=' + str(ticklen - 1) + 'q7F ^=1' #TODO: repeat whatever the hell q actually is
			txt += '=' + str(ticklen)
		else:
			txt += '=' + str(ticklen)
		return txt
		
	def convert(self):
		for c in range(0, 8):
			self.append('#' + str(c) + '  ')
			for e in range(0, len(self.event_table.events[c]) - 1):
				event = self.event_table.events[c][e]
				next = self.event_table.events[c][e + 1]
				next2 = self.event_table.events[c][e + 1]
				i = 0
				while e + 1 + i < len(self.event_table.events[c]) and (self.event_table.events[c][e + 1 + i].effect == 'patt' or self.event_table.events[c][e + 1 + i].effect == 'bar'):
					next2 = self.event_table.events[c][e + 1 + i]
					i += 1
				ticklen = int(Config.flag('tmult') * next.tick) - int(Config.flag('tmult') * event.tick)
				ticklen2 = int(Config.flag('tmult') * next2.tick) - int(Config.flag('tmult') * event.tick)
				self.set_mml_cmd(c, event.effect, event.value, ticklen, ticklen2, event.tick)
			self.append('\n\n')
		
	def save(self, filename):
		file = open(filename, 'w')
		file.write(self.txt)
		file.close()
	
if len(sys.argv) < 2:
	print('Usage: python3 it2amk.py <module_file> <flags>')
	sys.exit(1)
elif len(sys.argv) >= 2 and len(sys.argv) % 2 != 0:
	print('Error: Missing flag argument.')
	sys.exit(1)
	
it = pyIT.ITfile()
it.open(sys.argv[1])
Config.get_module_flags(it)
	
i = 2
while i < len(sys.argv):
	flag = sys.argv[i]
	arg = sys.argv[i + 1]
	
	try:
		Config.set_flag(flag, arg)
	except ValueError as e:
		print('Error: ' + str(e))
		sys.exit(1)
	except KeyError as e:
		print('Error: ' + str(e))
		sys.exit(1)
	
	i += 2
	
try:
	evtbl = EventTable(it)
	mml = MML(evtbl)
	mml.save('music/' + sys.argv[1].split('.')[0].replace('\\', '/').split('/')[-1] + '.mml')
except CompileErrorException as e:
	print('Error:', e)