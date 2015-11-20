#!/usr/bin/python

class CSVError(Exception):
    """A simple exception class for use in our CSV handling"""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class CSVReader(object):
    """A reader for the CSV input files"""
    def __init__(self, source):
        """
        Initialize with the source of CSV input and the destination for output.
        Defaults to sys.stdin and sys.stdout, respectively.
        """

        self.source = source
        self.lineno = 0
        self.lastline = None

    def readline(self):
        """
        Read a line of input and return it. Also track line number and last
        line read for diagnostic use.
        """

        self.lastline = self.source.readline()
        if len(self.lastline) != 0:
            self.lineno += 1
        return self.lastline

    def get_reader_state(self):
        """
        Get the diagnostic info for the current file and read state and format
        it as a string for warnings and such.
        """

        return "%s:%s: %s" % (self.source.name, self.lineno, str(self.lastline).strip())

    def parse_line(self):
        """
        Our basic CSV scanner state machine. We handle the following conventions:
        * "quoted strings","as fields",mixed,with,non-quoted
        * "double ""quote"" escapes"
        * Elimination of blank input lines
        * Leading and trailing whitespace stripping on fields
        """

        while True:
            line = self.readline()
            if len(line) == 0:
                return None
            line = line.strip()
            if len(line) == 0:
                continue
            state = None
            accum = ""
            values = []
            for c in line:
                if state is None:
                    if c == '"':
                        state = "quote"
                    elif c == ',':
                        values.append(accum.strip())
                        accum = ""
                    else:
                        accum += c
                        state = "data"
                elif state == "quote":
                    if c == '"':
                        state = "end_quote"
                    else:
                        accum += c
                elif state == "end_quote":
                    if c == '"':
                        state = "quote"
                        accum += c
                    elif c == ',':
                        values.append(accum.strip())
                        accum = ""
                        state = None
                    elif c.isspace():
                        pass
                    else:
                        raise CSVError("Unexpected character '%s' after end-quote" % c)
                elif state == "data":
                    if c == ',':
                        values.append(accum.strip())
                        accum = ""
                        state = None
                    elif c == '"' and accum.isspace():
                        accum = ""
                        state = "quote"
                    else:
                        accum += c
                else:
                    raise CSVError("Unknown state '%s'" % state)
            values.append(accum.strip())

            return values
