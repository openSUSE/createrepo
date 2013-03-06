#!/usr/bin/python
# util functions for createrepo
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.



import os
import os.path
import sys
import bz2
import gzip
import subprocess
from gzip import write32u, FNAME
from yum import misc

def errorprint(stuff):
    print >> sys.stderr, stuff

def _(args):
    """Stub function for translation"""
    return args


class GzipFile(gzip.GzipFile):
    def _write_gzip_header(self):
        # Generate a header that is easily reproduced with gzip -9 -n on
        # an unix-like system
        self.fileobj.write('\037\213')             # magic header
        self.fileobj.write('\010')                 # compression method
        self.fileobj.write('\000')                 # flags
        write32u(self.fileobj, long(0))            # timestamp
        self.fileobj.write('\002')                 # max compression
        self.fileobj.write('\003')                 # UNIX


class LzmaFile:
    def __init__(self, filename, mode, compresslevel=None):
        if mode != "w" and mode != "wb":
            raise NotImplementedError("Only writing of lzma files is supported")
        self.file = open(filename, mode)
        cmd = ["lzma"]
        if compresslevel:
                cmd.append("-%d" % compresslevel)
        self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                stdout=self.file)
        return

    def write(self, text):
        self.process.stdin.write(text)
        return

    def close(self):
        self.process.stdin.close()
        self.file.close()
        return

class HybridFile:
    def __init__(self, filename, mode):
        if filename.endswith(".gz"):
            filename = filename[:-3]
        if filename.endswith(".lzma"):
            filename = filename[:-5]
        self.lzma = GzipFile(filename + ".gz", mode)
        self.gz = LzmaFile(filename + ".lzma", mode)
        return

    def write(self, text):
        self.gz.write(text)
        self.lzma.write(text)
        return

    def close(self):
        self.gz.close()
        self.lzma.close()
        return


def _gzipOpen(filename, mode="rb", compresslevel=9):
    return GzipFile(filename, mode, compresslevel)

def bzipFile(source, dest):

    s_fn = open(source, 'rb')
    destination = bz2.BZ2File(dest, 'w', compresslevel=9)

    while True:
        data = s_fn.read(1024000)

        if not data: break
        destination.write(data)

    destination.close()
    s_fn.close()


def returnFD(filename):
    try:
        fdno = os.open(filename, os.O_RDONLY)
    except OSError:
        raise MDError, "Error opening file"
    return fdno

def checkAndMakeDir(directory):
    """
     check out the directory and make it, if possible, return 1 if done, else return 0
    """
    if os.path.exists(directory):
        if not os.path.isdir(directory):
            #errorprint(_('%s is not a dir') % directory)
            result = False
        else:
            if not os.access(directory, os.W_OK):
                #errorprint(_('%s is not writable') % directory)
                result = False
            else:
                result = True
    else:
        try:
            os.mkdir(directory)
        except OSError, e:
            #errorprint(_('Error creating dir %s: %s') % (directory, e))
            result = False
        else:
            result = True
    return result

def checksum_and_rename(fn_path, sumtype='sha256'):
    """checksum the file rename the file to contain the checksum as a prefix
       return the new filename"""
    csum = misc.checksum(sumtype, fn_path)
    fn = os.path.basename(fn_path)
    fndir = os.path.dirname(fn_path)
    csum_fn = csum + '-' + fn
    csum_path = os.path.join(fndir, csum_fn)
    os.rename(fn_path, csum_path)
    return (csum, csum_path)



def encodefilenamelist(filenamelist):
    return '/'.join(filenamelist)

def encodefiletypelist(filetypelist):
    result = ''
    ftl = {'file':'f', 'dir':'d', 'ghost':'g'}
    for x in filetypelist:
        result += ftl[x]
    return result

def split_list_into_equal_chunks(seq, num_chunks):
    avg = len(seq) / float(num_chunks)
    out = []
    last = 0.0
    while last < len(seq):
        out.append(seq[int(last):int(last + avg)])
        last += avg

    return out


class MDError(Exception):
    def __init__(self, value=None):
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        return self.value
