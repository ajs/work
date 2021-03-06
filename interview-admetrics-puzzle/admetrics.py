#!/usr/bin/python

# This is a module for reading and processing CSV files that describe ad
# unit performance. At the end, there is a sample output producer, but
# it's a relatively trivial thing and could be re-implemented for any
# number of purposes.

# The primary interface to this module is the AdDataReader class, which
# takes two parameters to instantiate: an input source and a producer
# function that will be called-back with the resulting AdInfo objects as
# the input is read.

# The second interface is the AdInfo object. It is instantiated with a
# warning callback, a field-ordering sequence, a data sequence and an
# optional CTR tolerance for comparing the input CTR to the calculated CTR.

# Warnings and errors are produced on standard output. Ad directed, this
# library errs on the side of producing copious diagnostic info (with line
# and context info) and exiting.

# A useful improvement for the future would be to behave more like a library in
# terms of throwing errors all the way up into the consumer, and let the
# consumer use callbacks to get any context information required. The way
# this is designed, that should be relatively easy to change.

# The spec didn't mention UTF-8, but the sample input and output files had a UTF-8
# BOM, so I have to assume that UTF-8 is required... I've done what I can
# in this respect, but more work may be required to fully support Unicode.

# Interestingly, Google's Ad Words report does not have a BOM, but perhaps
# the sample data files were given one just for purposes of the test? Or perhaps
# another ad vendor uses Unicode BOMs?

# Some thoughts on correctness:
#
# * I'm pretty blithly slinging around Unicode strings, and I'm sure
#   that somewhere I'm doing it wrong or incorrectly mixing Unicode
#   data and non-Unicode data. That might bite me if the input were
#   non-ascii-range characters. Testing needed.
# * I tried comparing the sample input to my own AdWords reports and
#   attempted to make this happier with data that looked like the real
#   world, but that could probably use work.
# * My CSV scanner is a rather hackish thing, but I didn't want to
#   pull in any non-core external depdendencies. The goal was to have
#   this work in any environment where a reasonably modern (2.6+) Python
#   is installed

import re
import sys
import codecs
import logging
import argparse

# Uncomment to suppress warnings
# logging.basicConfig(level=logging.ERROR)

#Utility functions:

CURRENCY_VALUE_RE = re.compile("-?\d+(\.\d\d)$")

def string_to_integer(s):
    """Convert a string to an integer, with error checking"""
    s = str(s).strip()
    if len(s) == 0:
        raise ValueError("Empty string as number")
    try:
        i = int(s)
    except ValueError:
        i = int(float(s))
    return i

def string_to_float(s):
    """Convert a string to a floating point value, with error checking"""
    s = str(s).strip()
    if len(s) == 0:
        raise ValueError("Empty string as number")
    f = float(s)
    return f

def money_string_to_float(s):
    """Convert a dollar value into a float"""
    s = str(s).strip()
    if len(s) == 0:
        raise ValueError("Empty string a money value")
    currency = s[0]
    if currency.isdigit():
        # AdWords seems to assume the currency of the account, and not
        # output it. Ick. We'll default to USD.
        currency = '$'
        s = '$' + s
    elif currency != "$":
        raise ValueError("TBD: No currency conversions available, yet")
    if len(s) == 1:
        raise ValueError("$ must be followed by numeric amount")
    value = s[1:]
    if re.match(CURRENCY_VALUE_RE, value):
        return string_to_float(value)
    else:
        raise ValueError("Currency value must be $d or $d.cc")

#############################
### The core library classes:

class AdInfo(object):
    """
    Definition as given by Cogo:
    Every day, the search engine provider sends you a CSV file that tells you the
    performance of your ads on the previous day. They provide four pieces of numeric
    data in the report: impressions (number of times each ad wa show),
    clicks (number of times someone clicked on the ad), CTR (clickthrough rate,
    or clicks/impressions), and total cost (amount they charged us for the clicks
    on that ad). We want to store the database table specified below. Note that we
    don't care about storing CTR because it can be derived from the other data.

    CREATE TABLE ad_report_data (
        report_date DATE NOT NULL,
        ad_group VARCHAR(255) NOT NULL,
        ad_name VARCHAR(255) NOT NULL,
        impressions INT NOT NULL,
        clicks INT NOT NULL,
        total_cost_in_cents INT NOT NULL,
        PRIMARY KEY(report_date, ad_group_ad_name))

    Note that the "ad_group_ad_name" above was in the original description, and
    appears to be a typo. I've sent off a request to confirm this...
    """

    def __init__(self, warner, ordering, csv, ctr_tolerance=4):
        """
        Represent an incoming datum of ad performance data. The parameters are:

        warner - a callback for issuing warnings
        ordering - a sequence of field names in the order that they will be expected
                   in the "csv" parameter. Names must be:
                    ad_group, ad_name, impressions, clicks, ctr, total_cost
        csv - A sequence of values that pairs with the ordering sequence, above.
              All values should be strings as they appeare in the input.
        ctr_tolerance - A number. The CTR will be rounded to the given precision
                        before error checking is applied.
        """

        self.warner = warner
        self.data = dict(zip(ordering, csv))
        self.date = self.data['date']
        self.ad_group = self.data['ad group']
        self.ad_name = self.data['ad name']
        self.impressions = string_to_integer(self.data['impressions'])
        self.clicks = string_to_integer(self.data['clicks'])
        self.ctr = self.data['ctr']
        # Google's AdWords report uses percent, not a raw ratio
        if self.ctr.endswith('%'):
            self.ctr = self.ctr[0:len(self.ctr)-1]
            self.ctr = string_to_float(self.ctr)/100.0
        else:
            self.ctr = string_to_float(self.data['ctr'])
        self.total_cost = money_string_to_float(self.data['total cost'])
        self._sanity_check(ctr_tolerance)

    def _sanity_check(self, ctr_tolerance):
        """
        Perform some sanity checks on the data, producing warnings or
        raising exceptions as required.
        """

        if self.impressions == 0:
            if self.ctr != 0:
                raise CSVError("Non-zero CTR for zero impressions")
        else:
            # Jitter lets us compensate for floating point error by allowing a small
            # variation between 0.333 and 1/3. This is configurable via the ctr_tolerance
            # parameter
            jitter = 10 ** -(ctr_tolerance-1)
            calc_ctr = float(self.clicks)/self.impressions
            delta = abs(round(self.ctr, ctr_tolerance)-round(calc_ctr, ctr_tolerance))
            if delta > jitter:
                self.warner(
                    "Given CTR (%f) does not match clicks/impressions (%f) to within %f" %
                        (self.ctr, calc_ctr, jitter))
        if self.total_cost == 0.0 and self.impressions > 0:
            raise CSVError("Sanity check failed: cost is non-zero for zero impressions")
        if self.total_cost < 0.0:
            raise CSVError("Sanity check failed: negative cost")
        if self.impressions < 0:
            raise CSVError("Sanity check failed: negative impressions")
        if self.clicks < 0:
            raise CSVError("Sanity check failed: negative clicks")
        if self.ad_group == "":
            raise CSVError("Sanity check failed: empty ad group")

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

class AdDataReader(CSVReader):
    """The specifics of our ad data parsing"""

    EXPECTED_FIELDS = {
        'ad group':'ad group',
        'ad name':'ad name',
        'ad':'ad name',
        'impressions':'impressions',
        'clicks':'clicks',
        'ctr':'ctr',
        'total cost':'total cost',
        'cost':'total cost',
    }

    # Ideally, I'd like to use a generic date parser for this, but
    # I wanted my submission to be free of external depedencies, and
    # the built-in Python date parser isn't robust enough to really
    # save me anything.
    DATE_MMDDYYYY_RE = re.compile(r"(\d\d?)/(\d\d?)/(\d{4})")
    DATE_ISO_RE = re.compile(r"(\d{4})-(\d\d)-(\d\d)")
    # Google's Adwords format
    DATE_SIMPLE_RE = re.compile(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d\d?),\s*(\d{4})",
        re.IGNORECASE)
    MONTH_MAP = {
        "jan":"01", "feb":"02", "mar":"03", "apr":"04", "may":"05", "jun":"06",
        "jul":"07", "aug":"08", "sep":"09", "oct":"10", "nov":"11", "dec":"12",
    }

    def __init__(self, source, produce, no_total_warning, *args):
        """
        Initialize the reader with an input source, a callback that will be
        invoked with the resulting AdInfo object from a line read from the data file,
        and a true/false flag for issuing warnings on lines that appear to be
        summary or total lines.

        The produce callback will be passed a named parameter, "first", which
        will be True the first time it is invoked for an output file and False
        each subsequent call.

        Additional, positional, parameters may optionally be receieved by the
        constructor, in which case they will be stored as a single sequence
        and passed on to the producer like so:

            produce(adinfo, first=isfirsttime, args=args)

        The input source must be a file object or compatible stream that supports
        .readline() and .name
        """

        self.produce = produce
        self.produce_args = args
        self.no_total_warning = no_total_warning
        self.date = None
        self.colnames = None
        self.accumulator = { 'clicks':0, 'impressions':0, 'total cost':0 }

        super(AdDataReader, self).__init__(source)

    def process_input(self):
        """Read in the CSV and call produce for each data line"""

        self._read_header()
        first = True
        while True:
            try:
                line = self.parse_line()
            except CSVError as e:
                self._failure("While reading data line", e.value)
                exit(1)
            if line is None:
                return
            line.append(self.date)
            try:
                # The tolerance value should be passed here, and recieved
                # from the caller that instantiated this class. Ideally, this
                # should be a command-line parameter, since it may vary by file
                row_data = AdInfo(self._warning, self.colnames, line)
            except CSVError as e:
                self._failure("While processing individual fields", e.value)
                exit(1)
            # The original sample input file used "Total" as an ad group to denote
            # the summary line. Google's Ad Sense reports use "--", so I handle both.
            if row_data.ad_group.lower() == 'total' or row_data.ad_group == "--":
                if not self.no_total_warning:
                    self._warning("Not saving input with ad group, '%s'" % row_data.ad_group)
                if row_data.impressions != self.accumulator['impressions']:
                    self._failure("Total impressions in summary (%d) != our tally (%d)" % (
                        row_data.impressions, self.accumulator['impressions']))
                if row_data.clicks != self.accumulator['clicks']:
                    self._failure("Total clicks in summary (%d) != our tally (%d)" % (
                        row_data.clicks, self.accumulator['clicks']))
                if abs(row_data.clicks - self.accumulator['clicks']) >= 0.01:
                    self._failure("Total cost in summary (%.2f) != our tally (%.2f)" % (
                        row_data.total_cost, self.accumulator['total cost']))
                continue
            else:
                if len(row_data.ad_name) == 0:
                    self._failure("Empty ad name not allowed")
                    exit(1)
                self.accumulator['impressions'] += row_data.impressions
                self.accumulator['clicks'] += row_data.clicks
                self.accumulator['total cost'] += row_data.total_cost
            if first:
                self.produce(row_data, first=True, args=self.produce_args)
                first = False
            else:
                self.produce(row_data, first=False, args=self.produce_args)

    def _read_header(self):
        """Read the header data including the report date and column names"""

        try:
            self.date = self._read_date_header()
        except CSVError as e:
            self._failure("While parsing date header", e.value)
            exit(1)
        try:
            self.colnames = self._read_column_names_header()
        except CSVError as e:
            self._failure("While parsing column names header", e.value)
            exit(1)

    def _read_date_header(self):
        """Read the date from the first line"""

        line = self.parse_line()
        if line is None:
            return None
        if len(line) > 1:
            self._warning("More than one column in date header")
        m = self.DATE_MMDDYYYY_RE.search(line[0])
        if m:
            return "%s-%s-%s" % m.group(3, 1, 2)
        m = self.DATE_ISO_RE.search(line[0])
        if m:
            return "%s-%s-%s" % m.group(1, 2, 3)
        m = self.DATE_SIMPLE_RE.search(line[0])
        if m:
            month = self.MONTH_MAP[m.group(1).lower()]
            day = m.group(2)
            if len(day) == 1:
                day = "0" + day
            year = m.group(3)
            return "%s-%s-%s" % (year, month, day)
        self._failure("Cannot find date in header", None)
        exit(1)

    def _read_column_names_header(self):
        """Read the header that keys our column names"""

        cols = self.parse_line()
        if cols is None:
            return None
        normalized_cols = [ self._normalize_column_name(col) for col in cols ]
        for key in self.EXPECTED_FIELDS.values():
            if key not in normalized_cols:
                raise CSVError("Cannot find required field in input: " + key)
        normalized_cols.append('date')
        return normalized_cols

    def _normalize_column_name(self, name):
        """Column names should be downcased and mapped to our expected names"""

        name = name.lower()
        if name in self.EXPECTED_FIELDS:
            name = self.EXPECTED_FIELDS[name]
        return name

    def _failure(self, message, exception=None):
        """Produce an error message"""

        if exception is not None:
            ex_msg = ":\n  " + exception
        else:
            ex_msg = "."
        logging.error(message + ":\n" + self.get_reader_state() + ex_msg)

    def _warning(self, message):
        """Produce a warning messsage"""

        logging.warning(self.get_reader_state() + "\n" + "Warning: " + message)


##########################################################
### What follows is a sample program that uses this module

# Tracker for our primary key
UNIQUE_RECORDS_SEEN = {}

def csv_string(in_string):
    """Format a string for CSV output"""

    if '"' in in_string:
        return '"' + in_string.replace('"', '""') + '"'
    else:
        return in_string

def output_encoded_string(s, codec):
    """Print a Unicode string as a given encoding on output."""

    sys.stdout.write((s + u"\n").encode(codec))

def default_producer(ad_info, first, args):
    """
    This will produce the output file as directed by the instructions. Note that
    the instructions were (deliberately?) vague about the output format, so most
    of what we know is from the sample data file.
    """

    if len(args) > 0:
        args = args[0]
        encoding = args.output_encoding
        bom = not args.no_output_bom
    else:
        encoding = 'utf-8'
        bom = True

    if first:
        if bom:
            if encoding == 'utf-8':
                sys.stdout.write(codecs.BOM_UTF8)
            elif encoding == 'utf-16':
                sys.stdout.write(codecs.BOM_UTF16)
            elif encoding == 'utf-16-be':
                sys.stdout.write(codecs.BOM_UTF16_BE)
            elif encoding == 'utf-16-le':
                sys.stdout.write(codecs.BOM_UTF16_LE)
            elif encoding == 'utf-32':
                sys.stdout.write(codecs.BOM_UTF32)
            elif encoding == 'utf-32-be':
                sys.stdout.write(codecs.BOM_UTF32_BE)
            elif encoding == 'utf-32-le':
                sys.stdout.write(codecs.BOM_UTF32_LE)
            else:
                logging.warning("Unicode BOM requested for unknown codec, '%s'" % encoding)

        output_encoded_string(u"report_date, ad_group, ad_name, impressions, " +
            "clicks, total_cost_in_cents", encoding)

    # Dollars to cents
    # Note that there is a great deal wrong with this, but a full treatment of correct
    # fractional currency handling is outside of the scope of this project right now.
    total_cost = int(round(ad_info.total_cost * 100))
    key = u"%s,%s,%s" % (
        ad_info.date,
        csv_string(ad_info.ad_group.lower()),
        csv_string(ad_info.ad_name.lower()),
    )

    global UNIQUE_RECORDS_SEEN
    if key in UNIQUE_RECORDS_SEEN:
        logging.error("Duplicate record for key: %s" % key)
        exit(1)
    UNIQUE_RECORDS_SEEN[key] = 1

    row = u"%s,%s,%s,%d,%d,%d" % (
        ad_info.date,
        csv_string(ad_info.ad_group.lower()),
        csv_string(ad_info.ad_name.lower()),
        ad_info.impressions,
        ad_info.clicks,
        total_cost,
    )
    output_encoded_string(row, encoding)

def main(argv):
    parser = argparse.ArgumentParser(description="ad metrics CSV processor")
    parser.add_argument('input', type=str, default='-', nargs='?',
        help="input file or '-' for stdin (default='utf-8')")
    parser.add_argument('--input-encoding', dest='input_encoding', action='store',
        default='utf-8', help="character encoding for input (default='utf-8')")
    parser.add_argument('--output-encoding', dest='output_encoding', action='store',
        default='utf-8', help="character encoding for output (default='utf-8')")
    parser.add_argument('--no-output-bom', dest='no_output_bom', action='store_true',
        default=False,
        help="do not output a Unicode BOM at start of output " + \
            "(--output-encoding=ascii will also disable BOM)")
    parser.add_argument('--no-total-warning', dest='no_total_warning',
        action='store_true', default=False,
        help="do not print a warning on summary lines")
    args = parser.parse_args()
    # Normalize encoding name per rules in codecs module
    args.output_encoding = args.output_encoding.lower()
    args.output_encoding.replace('_','-')
    if args.input == '-':
        inputfile = sys.stdin
    else:
        inputfile = open(args.input, "r")
    if args.output_encoding == "ascii":
        args.no_output_bom = True
    reader = AdDataReader(
        codecs.getreader(args.input_encoding)(inputfile),
        default_producer,
        args.no_total_warning,
        args)
    reader.process_input()

if __name__ == "__main__":
    main(sys.argv)
