'''
ARK: Survival Evolved Toolkit

Only supports Python3, Python2 is end of life and outdated thus not supported.

Purpose:
  Provide a Python toolkit for ARK. Originally designed to unpack the workshop archives.

Notice:
  I use PEP 8 as per it was intended; if you want to PEP 8 me read it first instead of being foolish: "A Foolish Consistency is the Hobgoblin of Little Minds"
'''


import struct
import zlib
import sys
import logging


__author__ = "James E"
__contact__ = "https://github.com/project-umbrella/arkit.py"
__copyright__ = "Copyright 2015, Project Umbrella"
__version__ = "0.0.0.1"
__status__ = "Prototype"
__date__ = "16 October 2015"
__license__ = "GPL v3.0 https://github.com/project-umbrella/arkit.py/blob/master/LICENSE"


logging.basicConfig(stream=sys.stderr, level=logging.CRITICAL)

class UnpackException(Exception):
    pass

class SignatureUnpackException(UnpackException):
    pass

class CorruptUnpackException(UnpackException):
    pass

def unpack(src, dst):
    '''
    Unpacks ARK's Steam Workshop *.z archives.

    Accepts two arguments:
        src = Source File/Archive
        dst = Destination File

    Error Handling:
        Currently logs errors via logging with an archive integrity as well as raising a custom exception. Also logs some debug and info messages.
        All file system errors are handled by python core.

    Process:
        1. Open the source file.
        2. Read header information from archive:
            - 00 (8 bytes) signature (6 bytes) and format ver (2 bytes)
            - 08 (8 byes) unpacked/uncompressed chunk size
            - 10 (8 bytes) packed/compressed full size
            - 18 (8 bytes) unpacked/uncompressed size
            - 20 (8 bytes) first chunk packed/compressed size
            - 26 (8 bytes) first chunk unpacked/uncompressed size
            - 20 and 26 repeat until the total of all the unpacked/uncompressed chunk sizes matches the unpacked/uncompressed full size.
        2. Read all the archive data and verify integrity (there should only be one partial chunk, and each chunk should match the archives header).
        3. Write the file.

    Development Note:
        - Not thoroughly tested for errors. There may be instances where this method may fail either to extract a valid archive or detect a corrupt archive.
        - Prevent overwriting files unless requested to do so.
        - Create a batch method.
    '''

    with open(src, 'rb') as f:
        sigver = struct.unpack('q', f.read(8))[0]
        unpacked_chunk = f.read(8)
        packed = f.read(8)
        unpacked = f.read(8)
        size_unpacked_chunk = struct.unpack('q', unpacked_chunk)[0]
        size_packed = struct.unpack('q', packed)[0]
        size_unpacked = struct.unpack('q', unpacked)[0]

        #Verify the integrity of the Archive Header
        if sigver == 2653586369:
            if isinstance(size_unpacked_chunk, int) and isinstance(size_packed , int) and isinstance(size_unpacked , int):
                logging.info("Archive is valid.")
                logging.debug("Archive header size information. Unpacked Chunk: {}({}) Full Packed: {}({}) Full Unpacked: {}({})".format(size_unpacked_chunk, unpacked_chunk, size_packed, packed, size_unpacked, unpacked))

                #Obtain the Archive Compression Index
                compression_index = []
                size_indexed = 0
                while size_indexed < size_unpacked:
                    raw_compressed = f.read(8)
                    raw_uncompressed = f.read(8)
                    compressed = struct.unpack('q', raw_compressed)[0]
                    uncompressed = struct.unpack('q', raw_uncompressed)[0]
                    compression_index.append((compressed, uncompressed))
                    size_indexed += uncompressed
                    logging.debug("{}: {}/{} ({}/{}) - {} - {}".format(len(compression_index), size_indexed, size_unpacked, compressed, uncompressed, raw_compressed, raw_uncompressed))

                if size_unpacked != size_indexed:
                    msg = "Header-Index mismatch. Header indicates it should only have {} bytes when uncompressed but the index indicates {} bytes.".format(size_unpacked, size_indexed)
                    logging.critical(msg)
                    raise CorruptUnpackException(msg)

                #Read the actual archive data
                data = b''
                read_data = 0
                for compressed, uncompressed in compression_index:
                    compressed_data = f.read(compressed)
                    uncompressed_data = zlib.decompress(compressed_data)

                    #Verify the size of the data is consistent with the archives index
                    if len(uncompressed_data) == uncompressed:
                        data += uncompressed_data
                        read_data += 1

                        #Verify there is only one partial chunk
                        if len(uncompressed_data) != size_unpacked_chunk and read_data != len(compression_index):
                            msg = "Index contains more than one partial chunk: was {} when the full chunk size is {}, chunk {}/{}".format(len(uncompressed_data), size_unpacked_chunk, read_data, len(compression_index))
                            logging.critical(msg)
                            raise CorruptUnpackException(msg)
                    else:
                        msg = "Uncompressed chunk size is not the same as in the index: was {} but should be {}.".format(len(uncompressed_data), uncompressed)
                        logging.critical(msg)
                        raise CorruptUnpackException(msg)
            else:
                msg = "Data types in the headers should be int's. Size Types: unpacked_chunk({}), packed({}), unpacked({})".format(sigver, type(size_unpacked_chunk), type(size_packed), type(size_unpacked))
                logging.critical(msg)
                raise CorruptUnpackException(msg)
        else:
            msg = "The signature and format version is incorrect. Signature was {} should be 2653586369.".format(sigver)
            logging.critical(msg)
            raise SignatureUnpackException(msg)

    #Write the extracted data to disk
    with open(dst, 'wb') as f:
        f.write(data)
    logging.info("Archive has been extracted.")
