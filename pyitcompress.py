# -*- coding: utf-8 -*-
"""
 * Schism Tracker - a cross-platform Impulse Tracker clone
 * copyright (c) 2003-2005 Storlek <storlek@rigelseven.com>
 * copyright (c) 2005-2008 Mrs. Brisby <mrs.brisby@nimh.org>
 * copyright (c) 2009 Storlek & Mrs. Brisby
 * URL: http://schismtracker.org/
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

#define NEED_BYTESWAP
#include "headers.h"
#include "fmt.h"

# ------------------------------------------------------------------------------------------------------------
# IT decompression code from itsex.c (Cubic Player) and load_it.cpp (Modplug)
# (I suppose this could be considered a merge between the two.)
import sys
import logging

class ReadBitsState:
    def __init__(self):
        self.bitbuf = 0
        self.bitnum = 0

def MIN(a, b):
    if a < b:
        return a
    else:
        return b

def it_readbits(n, state, stream):
    value = 0
    i = n
    
    #log = logging.getLogger("pyitcompress.it_readbits")
    #log.debug("bitnum=%d, bitbuf=%d, n=%d" % (state.bitnum, state.bitbuf, n))
    
    # this could be better
    while i:
        i -= 1
        if not state.bitnum:
            state.bitbuf = ord(stream.read(1))
            state.bitnum = 8
        value >>= 1
        #logging.debug("state.bitbuf = 0x%x, state.bitbuf<<31 = 0x%x" % (state.bitbuf, state.bitbuf<<31))
        value |= (state.bitbuf << 31) & 0xffffffff
        state.bitbuf >>= 1
        state.bitnum -= 1

    return value >> (32 - n)

##
## Converting an unsigned value to a signed one.
##
#
# byte_signer_pack = struct.Struct("@B")
# byte_signer_unpack = struct.Struct("@b")
#
# >>> def signbyte(b): return b - 256 if b > 127 else b
# ...
# >>> def signbyte_s(b): return byte_signer_unpack.unpack(byte_signer_pack.pack(b))[0]
# ...
# >>> def signbyte_s2(b): return struct.unpack("@b", struct.pack("@B", b))[0]
# ...
# >>> timeit.repeat(lambda: signbyte(234))
# [0.3214220080452037, 0.3246569789375826, 0.3103202065507844]
# >>> timeit.repeat(lambda: signbyte_s(234))
# [0.665931344571618, 0.6369421357301803, 0.6587316597669997]
# >>> timeit.repeat(lambda: signbyte_s2(234))
# [0.8120824689951291, 0.7978116412757572, 0.7951949434834091]
#
##
## Word (16-bit) conversions have similar characteristics.
##

def signbyte(b):
    return b - 256 if b > 127 else b

def unsignbyte(b):
    #logging.getLogger("pyitcompress.unsignbyte").debug("converting %d" % (b,))
    return b & 0xff

def signword(w):
    #logging.getLogger("pyitcompress.signword").debug("converting %d" % (b,))
    return w - 65536 if w > 32767 else w

def unsignword(w):
    #logging.getLogger("pyitcompress.unsignword").debug("converting %d" % (b,))
    return w & 0xffff

def it_decompress8(dest, len, srcbuf, it215):
    """
    dest: (file-like object) output buffer for decompressed data
    len: number of samples
    srcbuf: (file-like object) input
    it215: (bool) use it215 algorithm
    
    RETURN: actual size (in bytes) of COMPRESSED data
    """
    
    #const uint8_t *filebuf     # source buffer containing compressed sample data
    #const uint8_t *srcbuf      # current position in source buffer
    #int8_t *destpos        # position in destination buffer which will be returned
    #uint16_t blklen        # length of compressed data block in samples
    #uint16_t blkpos        # position in block
    #uint8_t width          # actual "bit width"
    #uint16_t value         # value read from file to be processed
    #int8_t d1, d2          # integrator buffers (d2 for it2.15)
    #int8_t v               # sample value
    
    state = ReadBitsState()    # state for it_readbits
    
    log = logging.getLogger("pyitcompress.it_decompress8")
    
    startpos = srcbuf.tell()
    #log.debug("startpos = %d" % (startpos,))
    
    # now unpack data till the dest buffer is full
    while (len):
        # read a new block of compressed data and reset variables
        # block layout: word size, <size> bytes data

        # removed: error handling when data is truncated
        if not srcbuf.read(2):
            return
            
        state.bitbuf = state.bitnum = 0
        
        blklen = MIN(0x8000, len)
        blkpos = 0

        #log.debug("new block, len = %d", blklen)
        
        width = 9 # start with width of 9 bits
        d1 = d2 = 0 # reset integrator buffers
        
        # now uncompress the data block
        while (blkpos < blklen):
            #log.debug("while2: blkpos = %d, blklen = %d" % (blkpos, blklen))
            
            value = it_readbits(width, state, srcbuf)
            
            if (width < 7):
                # method 1 (1-6 bits)
                #log.debug("method 1: width=0x%x, value=0x%x" % (width, value))
                # check for "100..."
                if (value == 1 << (width - 1)):
                    # yes!
                    value = it_readbits(3, state, srcbuf) + 1 # read new width
                    width = value if (value < width) else value + 1 # and expand it
                    continue # ... next value
            elif (width < 9):
                # method 2 (7-8 bits)
                #log.debug("method 2: width=0x%x, value=0x%x" % (width, value))
                border = (0xFF >> (9 - width)) - 4 # lower border for width chg
                if (value > border and value <= (border + 8)):
                    value -= border # convert width to 1-8
                    width =  value if (value < width) else value + 1 # and expand it
                    continue # ... next value
            elif (width == 9):
                # method 3 (9 bits)
                # bit 8 set?
                #log.debug("method 3: width=0x%x, value=0x%x" % (width, value))
                if (value & 0x100):
                    width = (value + 1) & 0xff # new width...
                    continue # ... and next value
            else:
                # illegal width, abort
                log.error("Illegal width")
                return

            # now expand value to signed byte
            if (width < 8):
                shift = 8 - width
                v = signbyte((value << shift) & 0xff)
                v >>= shift
                v = (v & 0xff)
            else:
                v = value & 0xff
            
            # integrate upon the sample values
            d1 = (d1 + v) & 0xff
            d2 = (d2 + d1) & 0xff
            
            # .. and store it into the buffer
            dest.write(chr(d2) if it215 else chr(d1))
            blkpos += 1

        # now subtract block length from total length and go on
        len -= blklen
    
    compressed_len = srcbuf.tell() - startpos
    #log.debug("size of compressed data: %d bytes" % (compressed_len))
    
    return compressed_len


def it_decompress16(dest, len, srcbuf, it215):
    """
    dest: (file-like object) output buffer for decompressed data
    len: number of samples
    srcbuf: (file-like object) input
    it215: (bool) use it215 algorithm
    """
    #const uint8_t *filebuf     # source buffer containing compressed sample data
    #const uint8_t *srcbuf      # current position in source buffer
    #int16_t *destpos        # position in destination buffer which will be returned
    #uint16_t blklen        # length of compressed data block in samples
    #uint16_t blkpos        # position in block
    #uint8_t width          # actual "bit width"
    #uint32_t value         # value read from file to be processed
    #int16_t d1, d2          # integrator buffers (d2 for it2.15)
    #int16_t v               # sample value
    state = ReadBitsState()    # state for it_readbits
    
    log = logging.getLogger("pyitcompress.it_decompress16")
    
    startpos = srcbuf.tell()
    #log.debug("startpos = %d" % (startpos,))

    # now unpack data till the dest buffer is full
    while (len):
        # read a new block of compressed data and reset variables
        # block layout: word size, <size> bytes data

        # removed: error handling when data is truncated
        if not srcbuf.read(2):
        	return

        state.bitbuf = state.bitnum = 0

        blklen = MIN(0x4000, len)
        blkpos = 0

        width = 17 # start with width of 17 bits
        d1 = d2 = 0 # reset integrator buffers

        # now uncompress the data block
        while (blkpos < blklen):
            value = it_readbits(width, state, srcbuf)
            
            if (width < 7):
                # method 1 (1-6 bits)
                # check for "100..."
                if (value == 1 << (width - 1)):
                    # yes!
                    value = it_readbits(4, state, srcbuf) + 1 # read new width
                    width = value if (value < width) else value + 1 # and expand it
                    continue # ... next value
            elif (width < 17):
                # method 2 (7-17 bits)
                border = (0xFFFF >> (17 - width)) - 8 # lower border for width chg
                if (value > border and value <= (border + 16)):
                    value -= border # convert width to 1-8
                    width =  value if (value < width) else value + 1 # and expand it
                    continue # ... next value
            elif (width == 17):
                # method 3 (17 bits)
                # bit 8 set?
                if (value & 0x10000):
                    width = (value + 1) & 0xff # new width...
                    continue # ... and next value
            else:
                # illegal width, abort
                log.error("Illegal width")
                return

            # now expand value to signed byte
            if (width < 16):
                shift = 16 - width
                v = signword((value << shift) & 0xffff)
                v >>= shift
            else:
                v = (value & 0xffff)
            
            # integrate upon the sample values
            d1 = (d1 + v) & 0xffff
            d2 = (d2 + d1) & 0xffff
            
            # .. and store it into the buffer
            outval = d2 if it215 else d1
            dest.write(chr(outval & 0xff))
            dest.write(chr(unsignbyte(outval >> 8)))
            blkpos += 1

        # now subtract block length from total length and go on
        len -= blklen

    compressed_len = srcbuf.tell() - startpos
    #log.debug("size of compressed data: %d bytes" % (compressed_len))
    
    return compressed_len

