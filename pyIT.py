#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""\

Python module for handling Impulse Tracker files.

(c) 2008 mike burke / mrb / mrburke@gmail.com

doesn't and won't handle old format IT instruments (cmwt < 0x200),
but I don't think these even exist in the wild.

creates an IT with the basic structure:
    IT header
    message
    patterns
    sample headers
    instruments
    sample data

todo:
 - add some compatibility-making code: fix envelopes that have no points, etc.
 - create some exceptions to replace assertion errors
 - remove redundant samples and instruments (already done for patterns)
 
"""

import os.path
import sys
import struct
from io import BytesIO
import traceback
import logging

#import psyco
#psyco.full()

import pyitcompress


class ITenvelope_node(object):
    def __init__(self):
        self.y_val = 0
        self.tick = 0
        
    def __len__(self):
        return 3
        
class ITenvelope(object):
    def __init__(self):
        
        self.IsOn = False
        self.LoopOn = False
        self.SusloopOn = False
        
        self.LpB = 0
        self.LpE = 0
        self.SLB = 0
        self.SLE = 0
        
        # xxx convert this to not have 25 nodes always, and remove numNodePoints;
        # the self.Nodes list should contain the number of node points
        self.numNodePoints = 0
        self.Nodes = [ITenvelope_node() for i in range(25)] # create 25 nodes

    def extraFlags(self):
        return 0
                
    def write(self, outf):
        flags = 0
        flags = flags | ((self.IsOn) << 0)
        flags = flags | ((self.LoopOn) << 1)
        flags = flags | ((self.SusloopOn) << 2)
        flags = flags | self.extraFlags()
    
        outf.write(struct.pack('<BBBB', flags, self.numNodePoints, self.LpB, self.LpE))
        outf.write(struct.pack('<BB', self.SLB, self.SLE))
        
        for node in self.Nodes:
            outf.write(struct.pack('<bH', node.y_val, node.tick))
        
        outf.write('\0')
    
    def load(self, inf):
        (flags, self.numNodePoints, self.LpB, self.LpE, self.SLB,
         self.SLE) = struct.unpack('<BBBBBB', inf.read(6))
        
        self.setFlags(flags)
        
        self.Nodes = []
        
        for i in range(25):
            node = ITenvelope_node()
            self.Nodes.append(node)
            (node.y_val, node.tick) = struct.unpack('<bH', inf.read(3))
        inf.read(1)
        
    def setFlags(self, flags):
        self.IsOn = bool(flags & 0x01)
        self.LoopOn = bool(flags & 0x02)
        self.SusloopOn = bool(flags & 0x04)
        
    def __len__(self):
        return 82
    
    
class ITvol_envelope(ITenvelope):
    def __init__(self):
        ITenvelope.__init__(self)

class ITpan_envelope(ITenvelope):
    def __init__(self):
        ITenvelope.__init__(self)

class ITpitch_envelope(ITenvelope):
    def __init__(self):
        ITenvelope.__init__(self)
        self.IsFilter = False
    
    def extraFlags(self):
        if self.IsFilter:
            return 0x80
        else:
            return 0
    
    def setFlags(self, flags):
        ITenvelope.setFlags(self, flags)
        self.IsFilter = bool(flags & 0x80)

class ITinstrument(object):
    def __init__(self):
        self.Filename = ''
        self.NNA = 0
        self.DCT = 0
        self.DCA = 0
        self.FadeOut = 0
        self.PPS = 0
        self.PPC = 0x3c
        self.GbV = 128
        self.DfP = 128
        self.RV = 0
        self.RP = 0
        # TrkVers and NoS are ignored (used in instrument files only)
        self.InstName = ''
        self.IFC = 0
        self.IFR = 0
        self.MCh = 0
        self.MPr = 0
        self.MIDIBank = 0
        
        self.SampleTable = [[i, 0] for i in range(120)]
        
        self.volEnv = ITvol_envelope()
        self.panEnv = ITpan_envelope()
        self.pitchEnv = ITpitch_envelope()
    
    def write(self, outf):
        outf.write(struct.pack('<4s12s', 'IMPI', self.Filename))
        outf.write(struct.pack('<BBBB', 0, self.NNA, self.DCT, self.DCA))
        outf.write(struct.pack('<HBB', self.FadeOut, self.PPS, self.PPC))
        outf.write(struct.pack('<BBBB', self.GbV, self.DfP, self.RV, self.RP))
        outf.write(struct.pack('<HBB', 0xadde, 0xbe, 0xef)) # unused data
        outf.write(struct.pack('<26s', self.InstName[:25]+'\0'))
        outf.write(struct.pack('<BBBBH', self.IFC, self.IFR, self.MCh, self.MPr, self.MIDIBank))
        for smp in self.SampleTable:
            outf.write(struct.pack('<BB', smp[0], smp[1]))
        
        self.volEnv.write(outf)
        self.panEnv.write(outf)
        self.pitchEnv.write(outf)
        
        outf.write('FOOB')
    
    def load(self, inf):
        
        """inf must be seeked to position of instrument to be read"""
        (IMPI, self.Filename) = struct.unpack('<4s12s', inf.read(16))
        assert(IMPI.decode('utf-8') == 'IMPI')
        self.Filename = self.Filename.decode('utf-8')
        
        (zero, self.NNA, self.DCT, self.DCA, self.FadeOut, self.PPS, self.PPC, 
         self.GbV, self.DfP, self.RV, self.RP, discard, discard,
         discard) = struct.unpack('<BBBBHBBBBBBHBB', inf.read(16))
        
        # seems some mods (saved by a bad schismtracker, maybe?)
        # don't have zero = 0x0
        #assert(zero == 0x0)
        
        self.InstName = inf.read(26).decode('utf-8').replace('\0', ' ')[:25]
        
        (self.IFC, self.IFR, self.MCh, self.MPr,
         self.MIDIBank) = struct.unpack('<BBBBH', inf.read(6))
        
        self.SampleTable = []
        for i in range(120):
            self.SampleTable.append(list(struct.unpack('<BB', inf.read(2))))
        
        self.volEnv = ITvol_envelope()
        self.panEnv = ITpan_envelope()
        self.pitchEnv = ITpitch_envelope()
        
        self.volEnv.load(inf)
        self.panEnv.load(inf)
        self.pitchEnv.load(inf)
        
        inf.read(4) # dummy read
        
        
    def __len__(self):
        return 554

class ITsample(object):
    def __init__(self):
        self.Filename = ''
        self.GvL = 64
        
        self.IsSample = False
        self.Is16bit = False
        self.IsStereo = False
        self.IsCompressed = False
        self.IsLooped = False
        self.IsSusLooped = False
        self.IsPingPongLoop = False
        self.IsPingPongSusLoop = False
        
        self.Vol = 64
        self.SampleName = ''
        self.Cvt = 0x01
        self.DfP = 0x00
        
        # length is determined by sample data
        # note, lengths and loop indices are in SAMPLES, not BYTES
        
        self.LoopBegin = 0
        self.LoopEnd = 0
        self.C5Speed = 8363
        self.SusLoopBegin = 0
        self.SusLoopEnd = 0
        self.ViS = 0
        self.ViD = 0
        self.ViT = 0
        self.ViR = 0
        
        self.SampleData = ''
        self.CompressedSampleData = None
        self._original_sample_data = self.SampleData
    
    def sampleDataLen(self):
        """
        Return the length of the sample data in SAMPLES.
        """
        divider = 1
        if self.Is16bit:
            divider = divider * 2
        if self.IsStereo:
            divider = divider * 2
            
        return len(self.SampleData) / divider
    
    def rawSampleData(self):
        """
        Return the raw sample data.
        
        If you are saving the sample data, this is the correct function to call
        as it will return the COMPRESSED data if possible.
        
        If you are modifying the sample data, DO NOT call this function; use
        SampleData directly. It's ok, I promise.
        """
        self._check_compression_status()
        
        if self.IsCompressed and self.CompressedSampleData is not None:
            return self.CompressedSampleData
        else:
            return self.SampleData
    
    def _check_compression_status(self):
        """
        Check if the data should be stored compressed.
        
        If modifications were made to the sample data, and it was compressed,
        we have to save it uncompressed, because re-compression is not
        implemented.
        
        However, if it wasn't modified, we try to re-save the original
        compressed data.
        """
        if self.IsCompressed and self.modified():
            self.IsCompressed = False
        
        
    def write(self, outf, sample_offset):
        log = logging.getLogger('pyIT.ITsample.save')
        
        if not self.IsSample:
            self.SampleData = ''
        
        self._check_compression_status()
        
        flags = 0
        flags = flags | ((self.IsSample) << 0)
        flags = flags | ((self.Is16bit) << 1)
        flags = flags | ((self.IsStereo) << 2)
        flags = flags | ((self.IsCompressed) << 3)
        flags = flags | ((self.IsLooped) << 4)
        flags = flags | ((self.IsSusLooped) << 5)
        flags = flags | ((self.IsPingPongLoop) << 6)
        flags = flags | ((self.IsPingPongSusLoop) << 7)

        #log.debug("     Cvt (convert) = 0x%02x" % (self.Cvt,))
        #log.debug("     Flg (flags) = 0x%02x" % (flags,))
        #self.Cvt = 0x01
        
        outf.write(struct.pack('<4s12s', 'IMPS', self.Filename))
        outf.write(struct.pack('<BBBB', 0, self.GvL, flags, self.Vol))
        outf.write(struct.pack('<26s', self.SampleName[:25]+'\0'))
        outf.write(struct.pack('<BB', self.Cvt, self.DfP))
        outf.write(struct.pack('<I', self.sampleDataLen()))
        outf.write(struct.pack('<III', self.LoopBegin, self.LoopEnd, self.C5Speed))
        outf.write(struct.pack('<II', self.SusLoopBegin, self.SusLoopEnd))
        outf.write(struct.pack('<I', sample_offset))
        outf.write(struct.pack('<BBBB', self.ViS, self.ViD, self.ViT, self.ViR))

    def load(self, inf):
        log = logging.getLogger('pyIT.ITsample.load')
        
        (IMPS, self.Filename) = struct.unpack('<4s12s', inf.read(16))
        self.Filename = self.Filename.decode('utf-8')
        assert(IMPS.decode('utf-8') == 'IMPS')
        
        (zero, self.GvL, flags, self.Vol) = struct.unpack('<BBBB', inf.read(4))
        # seems some mods (saved by a bad schismtracker, maybe?)
        # don't have zero = 0x0
        #assert(zero == 0x0)
        
        self.IsSample = bool(flags & 0x01)
        self.Is16bit = bool(flags & 0x02)
        self.IsStereo = bool(flags & 0x04)
        self.IsCompressed = bool(flags & 0x08)
        self.IsLooped = bool(flags & 0x10)
        self.IsSusLooped = bool(flags & 0x20)
        self.IsPingPongLoop = bool(flags & 0x40)
        self.IsPingPongSusLoop = bool(flags & 0x80)
        
        self.SampleName = inf.read(26).decode('utf-8').replace('\0', ' ')[:25]
        
        log.debug("=> Loading sample %s" % (self.SampleName,))
        
        (self.Cvt, self.DfP) = struct.unpack('<BB', inf.read(2))
        log.debug("     Cvt (convert) = 0x%02x" % (self.Cvt,))
        self.IT215Compression = self.IsCompressed and bool(self.Cvt & 0x04)
        
        (length, self.LoopBegin, self.LoopEnd, self.C5Speed) = struct.unpack('<IIII', inf.read(16))
        (self.SusLoopBegin, self.SusLoopEnd, offs_sampledata, self.ViS,
         self.ViD, self.ViT, self.ViR) = struct.unpack('<IIIBBBB', inf.read(16))
        
        # load sample, if there is one
        if self.IsSample and length > 0:
            # first, find length in bytes (not samples!)
            mult = 1
            if self.Is16bit:
                mult = mult * 2
            if self.IsStereo:
                mult = mult * 2
            
            log.debug("     length in samples is %d" % (length,))
            if self.IsCompressed:
                log.debug("     compressed!")
                
                # real sample decompression
                decompressedbuf = StringIO()
                
                if self.Is16bit:
                    decompressor = pyitcompress.it_decompress16
                    log.debug("     16-bit compressed sample at %d" % (offs_sampledata,))
                else:
                    decompressor = pyitcompress.it_decompress8
                    log.debug("     8-bit compressed sample at %d" % (offs_sampledata,))
                    
                inf.seek(offs_sampledata)
                
                try:
                    # Load compressed sample
                    if self.IT215Compression:
                        log.debug("     IT 2.15 sample compression")
                    
                    compressed_len = decompressor(decompressedbuf, length, inf, self.IT215Compression)
                    self.SampleData = decompressedbuf.getvalue()
                    log.debug("     compressed length: %d; decompressed length: %d" % (compressed_len, len(self.SampleData)))
                    
                    # Load actual compressed sample data in case we want
                    # to re-save it later
                    inf.seek(offs_sampledata)
                    self.CompressedSampleData = inf.read(compressed_len)
                    
                    # Retain reference to original sample data; we can use
                    # this with modified() to determine if the sample was
                    # modified.
                    # 
                    # This is used later for re-saving compressed data.
                    self._original_sample_data = self.SampleData
                    
                except:
                    print()
                    traceback.print_exc()
            else:
                # Load uncompressed sample
                length = length * mult
                log.debug("     length in bytes is %s" % (length,))
                inf.seek(offs_sampledata)
                self.SampleData = inf.read(length)
                self.CompressedSampleData = None
                self._original_sample_data = self.SampleData
            
    def modified(self):
        return (self.SampleData is not self._original_sample_data)
        
    def __len__(self):
        return 80
    
class ITnote(object):
    def __init__(self):
        self.Note = None
        self.Instrument = None
        self.Volume = None
        self.Effect = None
        self.EffectArg = None
    
    def __eq__(self, other):
        return (self.Note == other.Note and
                self.Instrument == other.Instrument and
                self.Volume == other.Volume and
                self.Effect == other.Effect and
                self.EffectArg == other.EffectArg)
        
    def __ne__(self, other):
        return not (self == other)
    
    def note_num_as_str(self, note_num):
        # C C# D D# E F F# G G# A A# B
        if self.Note is None:
            return '...'
        if self.Note == 254:
            return '^^^'
        if self.Note == 255:
            return '==='
        
        note_list = [
            'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        pitch = note_list[note_num % 12]
        octave = note_num / 12
        
        return ('%-2s%d' % (pitch, octave)).replace(' ', '-')
    
    def __str__(self):
        if self.Instrument is None:
            instrument = ".."
        else:
            instrument = "%02d" % self.Instrument
        if self.Volume is None:
            volume = ".."
        else:
            volume = "%02d" % self.Volume
            
        if self.Effect is None:
            effect = ".."
        else:
            effect = "%02d" % self.Effect
            
        if self.EffectArg is None:
            effectarg = ".."
        else:
            effectarg = "%02x" % self.EffectArg
            
        return "%s %s %s %s%s" % (self.note_num_as_str(self.Note),
                                 instrument,
                                 volume,
                                 effect,
                                 effectarg
                                )
    
    
class ITpattern(object):
    def __init__(self):
        # Fill pattern with a bunch of empty ITnote instances.
        # self.Rows[4][2] would return the note on the third channel in 
        # the fifth row.
        self.Rows = [[ITnote() for i in range(64)] for j in range(64)]

    def __len__(self):
        return len(self.pack()) + 8
    
    def __eq__(self, other):
        return self.Rows == other.Rows
    
    def __ne__(self, other):
        return not (self == other)
    
    def isEmpty(self):
        """ 'empty' here uses the IT definition of a 64-row pattern with no note data. """
        return self == ITpattern()
        
    def write(self, outf):
        ptndata = self.pack()
        outf.write(struct.pack('<HH4s', len(ptndata), len(self.Rows), '\0'*4))
        outf.write(ptndata)
    
    def unpack(self, rows, ptndata):
        """
        Unpack the raw pattern data stored in self.ptnData.
        """
        
        log = logging.getLogger("pyIT.ITpattern.unpack")

        log.info("load pattern: rows = %d, len = %d" %(rows, len(ptndata),))
        
        ptn_reader = BytesIO(ptndata)
        masks = [0] * 64 # prepare mask variables
        last_note = [ITnote() for i in range(64)] # last note storage
        
        # Reset row data
        self.Rows = [[ITnote() for i in range(64)] for j in range(rows)]
        
        row_num = 0
        
        while True:
            chan_data = ptn_reader.read(1)
            
            if chan_data == b'': # end of data
                break
            
            chan_data = struct.unpack('<B', chan_data)[0]
            
            if chan_data == 0: # end of row
                row_num = row_num + 1
                continue
            
            chan_num = (chan_data-1) & 63 # get channel number for this data
            
            if chan_data & 128: # new value for this channel's mask variable
                masks[chan_num] = struct.unpack('<B', ptn_reader.read(1))[0]
            
            mask = masks[chan_num]
            if mask & 1:
                self.Rows[row_num][chan_num].Note = struct.unpack('<B', ptn_reader.read(1))[0]
                last_note[chan_num].Note = self.Rows[row_num][chan_num].Note
            if mask & 2:
                self.Rows[row_num][chan_num].Instrument = struct.unpack('<B', ptn_reader.read(1))[0]
                last_note[chan_num].Instrument = self.Rows[row_num][chan_num].Instrument
            if mask & 4:
                self.Rows[row_num][chan_num].Volume = struct.unpack('<B', ptn_reader.read(1))[0]
                last_note[chan_num].Volume = self.Rows[row_num][chan_num].Volume
            if mask & 8:
                (self.Rows[row_num][chan_num].Effect,
                 self.Rows[row_num][chan_num].EffectArg) = struct.unpack('<BB', ptn_reader.read(2))
                last_note[chan_num].Effect = self.Rows[row_num][chan_num].Effect
                last_note[chan_num].EffectArg = self.Rows[row_num][chan_num].EffectArg
            if mask & 16:
                self.Rows[row_num][chan_num].Note = last_note[chan_num].Note
            if mask & 32:
                self.Rows[row_num][chan_num].Instrument = last_note[chan_num].Instrument
            if mask & 64:
                self.Rows[row_num][chan_num].Volume = last_note[chan_num].Volume
            if mask & 128:
                self.Rows[row_num][chan_num].Effect = last_note[chan_num].Effect
                self.Rows[row_num][chan_num].EffectArg = last_note[chan_num].EffectArg
            
        
        #row_num = 0
        #for row in self.Rows:
        #    pretty_row = ' | '.join([str(row[x]) for x in xrange(4)])
        #    log.debug("Row %02d: %s" % (row_num, pretty_row))
        #    row_num = row_num + 1
                
    def pack(self):
        """
        Pack pattern data back and return it as a string of raw data.
        """
        log = logging.getLogger("pyIT.ITpattern.unpack")

        ptn_writer = StringIO()
        masks = [0] * 64 # prepare mask variables
        last_note = [ITnote() for i in range(64)] # last note storage
        empty_note = ITnote()
        
        for row_data in self.Rows:
            for chan_num in range(64):
                # Anything in channel?
                note = row_data[chan_num]
                if note == empty_note:
                    continue
                
                # Find out what mask variable should be, and pack note data
                # in a temporary StringIO.
                # 
                # This needs to be stored in a temporary place, as chan_data
                # and mask won't be known until after we've looked at the
                # entire note.
                mask = 0
                packed_note = StringIO()
                
                if note.Note is not None:
                    if note.Note == last_note[chan_num].Note:
                        mask |= 16
                    else:
                        packed_note.write(struct.pack('<B', note.Note))
                        last_note[chan_num].Note = note.Note
                        mask |= 1
                if note.Instrument is not None:
                    if note.Instrument == last_note[chan_num].Instrument:
                        mask |= 32
                    else:
                        packed_note.write(struct.pack('<B', note.Instrument))
                        last_note[chan_num].Instrument = note.Instrument
                        mask |= 2
                if note.Volume is not None:
                    if note.Volume == last_note[chan_num].Volume:
                        mask |= 64
                    else:
                        packed_note.write(struct.pack('<B', note.Volume))
                        last_note[chan_num].Volume = note.Volume
                        mask |= 4
                if note.Effect is not None or note.EffectArg is not None:
                    if (note.Effect == last_note[chan_num].Effect and 
                        note.EffectArg == last_note[chan_num].EffectArg):
                        mask |= 128
                    else:
                        mask |= 8
                        write_effect = note.Effect
                        write_effectarg = note.EffectArg
                        if write_effect is None:
                            write_effect = 0
                        if write_effectarg is None:
                            write_effectarg = 0
                            
                        last_note[chan_num].Effect = write_effect
                        last_note[chan_num].EffectArg = write_effectarg
                        
                        packed_note.write(struct.pack('<BB',
                                                      write_effect,
                                                      write_effectarg))
                
                # Check if we will reuse last mask
                if mask == masks[chan_num]:
                    ptn_writer.write(struct.pack('<B', (chan_num + 1)))
                else:
                    ptn_writer.write(struct.pack('<BB',
                                        (chan_num + 1) | 128,
                                        mask))
                    masks[chan_num] = mask
                ptn_writer.write(packed_note.getvalue())
                
            
            # Write end-row marker.
            ptn_writer.write("\x00")
        
        return ptn_writer.getvalue()
        
        
    def load(self, inf):
        """Load IT pattern data from inf.  inf should already be seeked to
           the offset of the pattern to be loaded."""
        (ptnlen, rows, discard) = struct.unpack('<HH4s', inf.read(8))
        ptndata = inf.read(ptnlen)
        
        self.unpack(rows, ptndata)
        
class ITfile(object):
    Orderlist_offs = 192 # length of IT header before any dynamic data (order list)
    pyIT_Cwt_v = 0x4101 # This value will be written into Cwt_v ("created with
                        # tracker version") upon write().
    
    def __init__(self):
        self.SongName = ''
        self.PHilight_minor = 4
        self.PHilight_major = 16
        
        # OrdNum, InsNum, SmpNum, PatNum are used only when loading files; 
        # the actual numbers will be stored as len(lists)
        
        self.Cwt_v = ITfile.pyIT_Cwt_v
        self.Cmwt = 0x0214
        self.Flags = 0x000d
        self.Special = 0x0006
        self.GV = 128    # global vol
        self.MV = 48     # mixing vol
        self.IS = 6        # initial speed
        self.IT = 125    # initial tempo
        self.Sep = 128 # stereo separation
        self.PWD = 0x00
        
        # msglen is also collected by actual message length
        self.Message = ''
        
        self.ChannelPans = 64*[32]
        self.ChannelVols = 64*[64]
        
        self.Orders = []
        
        self.Instruments = []
        self.Samples = []
        self.Patterns = []

    def open(self, infilename):
        log = logging.getLogger("pyIT.ITfile.open")
        inf = open(infilename, "rb")
        
        buf = inf.read(30)
        (IMPM, self.SongName) = struct.unpack('<4s26s', buf)
        IMPM = IMPM.decode('utf-8')
        self.SongName = self.SongName.decode('utf-8')
        
        assert(IMPM == 'IMPM')
        
        self.SongName = self.SongName.split('\0')[0]
        
        buf = inf.read(34)
        (self.PHilight_minor, self.PHilight_major, n_ords, n_insts, n_samps,
         n_ptns, self.Cwt_v, self.Cmwt, self.Flags, self.Special, self.GV, self.MV,
         self.IS, self.IT, self.Sep, self.PWD, msglen, offs_msg, reserved) = struct.unpack(
         '<BBHHHHHHHHBBBBBBHII', buf)
        
        offs_ords = ITfile.Orderlist_offs
        offs_instoffs = offs_ords + n_ords
        offs_sampoffs = offs_instoffs + n_insts*4
        offs_ptnoffs = offs_sampoffs + n_samps*4
        
        
        assert(inf.tell() == 0x40)
        
        self.ChannelPans = []
        for i in range(64):
            self.ChannelPans.append(struct.unpack('<B', inf.read(1))[0])
        
        self.ChannelVols = []
        for i in range(64):
            self.ChannelVols.append(struct.unpack('<B', inf.read(1))[0])
        
        assert(inf.tell() == offs_ords)
        
        self.Orders = []
        for i in range(n_ords):
            self.Orders.append(struct.unpack('<B', inf.read(1))[0])
        
        assert(inf.tell() == offs_instoffs)
        
        offs_insts = []
        for i in range(n_insts):
            offs_insts.append(struct.unpack('<I', inf.read(4))[0])
        
        assert(inf.tell() == offs_sampoffs)
        
        offs_samps = []
        for i in range(n_samps):
            offs_samps.append(struct.unpack('<I', inf.read(4))[0])
        
        assert(inf.tell() == offs_ptnoffs)
        
        offs_ptns = []
        for i in range(n_ptns):
            offs_ptns.append(struct.unpack('<I', inf.read(4))[0])
        
        # load song message
        
        if (self.Special & 0x0001) and (msglen > 0):
            inf.seek(offs_msg)
            self.Message = inf.read(msglen).decode('utf-8').replace('\0', ' ').replace('\r', '\n')[:-1]
        else:
            self.Message = ''
        
        # load patterns
        
        self.Patterns = []
        
        for offs_ptn in offs_ptns:
            ptn = ITpattern()
            if offs_ptn != 0:
                inf.seek(offs_ptn)
                
                ptn.load(inf)
                
            self.Patterns.append(ptn)
        
        # load instruments
        
        self.Instruments = []
        
        for offs_inst in offs_insts:
            inf.seek(offs_inst)
            
            inst = ITinstrument()
            try:
                inst.load(inf)
            except Exception as e:
                raise e
                # the instrument failed to load, but we'll pretend it didn't
                pass
            self.Instruments.append(inst)
        
        self.Samples = []
        
        for offs_samp in offs_samps:
            inf.seek(offs_samp)
            
            samp = ITsample()
            try:
                samp.load(inf)
            except Exception as e:
                raise e
                # the sample failed to load, but we'll pretend it didn't
                # we might need to do some cleanup...
                
                pass
            self.Samples.append(samp)
        
        inf.close()
        
    def write(self, outfilename):
        log = logging.getLogger("pyIT.ITfile.write")
        outf = open(outfilename, "wb")
        
        # This is a comment. I like comments.
        if (len(self.Message) > 0):
            self.Special = self.Special | 0x0001
            message = self.Message.replace('\n', '\r') + '\0'
        else:
            self.Special = self.Special & (~0x0001)
            message = ''

        # We set "Compatible with" to IT 2.15 when saving IT 2.15 samples,
        # so that modplug-based loaders knows what the hell is up.
        # 
        # Let's scan all our samples to see.

        self.Cwt_v = ITfile.pyIT_Cwt_v
        
        self.Cmwt = 0x0214
        for sample in self.Samples:
            sample._check_compression_status()
            if sample.IsCompressed and sample.IT215Compression:
                log.debug("Song contains at least one IT 2.15 sample; setting cmwt == 0x0215")
                self.Cmwt = 0x0215
                break
        
        instoffs_offs = ITfile.Orderlist_offs + len(self.Orders)
        sampoffs_offs = instoffs_offs + len(self.Instruments)*4
        ptnoffs_offs = sampoffs_offs + len(self.Samples)*4
        msg_offs = ptnoffs_offs + len(self.Patterns)*4
        ptn_offs = msg_offs + len(message)
        
        # pack patterns so we can predict total pattern data length, and
        # next offset
        (pattern_list, unique_ITpatterns) = self.pack_ptns()
        ptn_offsets = {} 
        offs = ptn_offs
        for x in pattern_list:
            if x is not False and x not in ptn_offsets:
                # unknown pattern
                
                # store new pattern offset
                ptn_offsets[x] = offs
                
                offs = offs + len(unique_ITpatterns[x])
        
        
        #samp_offs = ptn_offs + sum([len(x) for x in self.Patterns])
        samp_offs = offs
        inst_offs = samp_offs + sum([len(x) for x in self.Samples])
        sampledata_offs = inst_offs + sum([len(x) for x in self.Instruments])
        
        # write header
        songname = self.SongName[:25].ljust(26, '\x00')
        
        outf.write(struct.pack('<4s26sBB', 'IMPM', songname, self.PHilight_minor, self.PHilight_major))
        outf.write(struct.pack('<HHHHHHHH', len(self.Orders), len(self.Instruments),
                                            len(self.Samples), len(self.Patterns),
                                            self.Cwt_v, self.Cmwt, self.Flags, self.Special))
        outf.write(struct.pack('<BBBBBBHII', self.GV, self.MV, self.IS, self.IT,
                                             self.Sep, self.PWD, len(message), msg_offs, 0))
        for x in self.ChannelPans:
            # x >= 128 == muted
            if (x > 64 and x < 128):
                x = 100 # surround
            elif x < 0:
                x = 0
            outf.write(struct.pack('<B', x))
        
        for x in self.ChannelVols:
            if (x > 64):
                x = 64
            elif x < 0:
                x = 0
            outf.write(struct.pack('<B', x))
        
        assert(outf.tell() == ITfile.Orderlist_offs)
        
        for x in self.Orders:
            if (x > 199):
                if (x < 254):
                    x = 199
                elif (x > 255):
                    x = 255
            elif x < 0:
                x = 0
            outf.write(struct.pack('<B', x))
        
        assert(outf.tell() == instoffs_offs)
        
        offs = inst_offs
        for x in self.Instruments:
            outf.write(struct.pack('<I', offs))
            offs = offs + len(x)
            
        assert(outf.tell() == sampoffs_offs)
        
        offs = samp_offs
        for x in self.Samples:
            outf.write(struct.pack('<I', offs))
            offs = offs + len(x)
        
        assert(outf.tell() == ptnoffs_offs)
        
        # save patterns (packed)
        for x in pattern_list:
            if x is False:
                log.debug("write empty pattern offs")
                ptnoffs = 0
            else:
                log.debug("write real pattern offs")
                ptnoffs = ptn_offsets[x]
                
            outf.write(struct.pack('<I', ptnoffs))
        
        assert(outf.tell() == msg_offs)
        if message:
            outf.write(message)
        assert(outf.tell() == ptn_offs)
        
        for ptn in unique_ITpatterns:
            log.debug("write pattern")
            ptn.write(outf)
        assert(outf.tell() == samp_offs)
        
        # next_smpoffs is the actual offset of the sample data for each sample.
        # It's stored in the header, so writing the header needs to know it.
        
        next_smpoffs = sampledata_offs
        for samp in self.Samples:
            samp.write(outf, next_smpoffs)
            next_smpoffs = next_smpoffs + len(samp.rawSampleData())
        eof = next_smpoffs
        
        assert(outf.tell() == inst_offs)
        
        for inst in self.Instruments:
            inst.write(outf)
        assert(outf.tell() == sampledata_offs)
        
        for samp in self.Samples:
            outf.write(samp.rawSampleData())
        
        assert(outf.tell() == eof)
                
        outf.close()
        
    def pack_ptns(self):
        """Returns a tuple(pattern_list, unique_ITpatterns)""" 
        ptnlist = []
        ptns = []
        
        for ptn in self.Patterns:
            if ptn.isEmpty():
                # empty pattern is empty
                ptnlist.append(False)
            elif ptn in ptns:
                # already in pattern set, create a reference only
                ptnlist.append(ptns.index(ptn))
            else:
                # doesn't exist in pattern set, add it and create a reference to it
                ptns.append(ptn)
                ptnlist.append(ptns.index(ptn))
        
        return (ptnlist, ptns) 

def process():
    #logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logging.basicConfig(level=logging.DEBUG, format="%(name)-24s %(levelname)-7s %(message)s")
    
    # pyitcompress is like, really noisy on the DEBUG channel,
    # and sample compression slows down a shitload if you let it print
    # all that shit to your screen.
    #logging.getLogger("pyitcompress").setLevel(level=logging.WARNING)
    
    itf = ITfile()
    
    assert(len(sys.argv) == 2)
    
    itf.open(sys.argv[1])

    #logging.info("Cwt_v is 0x%04x" % (itf.Cwt_v,))
    
    ## set all samples to "uncompressed" (should prevent re-saving of
    ## compressed samples in favour of uncompressed versions)
    for samp in itf.Samples:
        samp.IsCompressed = False
    
    ## modify all samples very slightly (should prevent re-saving of compressed
    ## samples in favour of uncompressed versions)
    #for samp in itf.Samples:
        #samp.SampleData = samp.SampleData + "\0\0\0\0"
    
    #for samp in itf.Samples:
    #    print samp.SampleName.decode('cp437')
    
    itf.write('new.it')
    
    # Create a mostly-empty .IT file
    #itf = ITfile()
    #itf.Orders.append(0)
    #itf.Instruments.append(ITinstrument())
    #itf.Instruments[0].Filename = 'fallow'
    #itf.Instruments[0].InstName = 'aaaaaa!!'
    #
    #itf.Samples.append(ITsample())
    #itf.Samples[0].Filename = 'HUUU'
    #itf.Samples[0].SampleName = 'Bubuuu!!!'
    #
    #itf.Message = 'ahahaha!'
    #itf.write('bloo.it')

if __name__ == '__main__':
    
    process()
