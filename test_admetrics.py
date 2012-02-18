#!/usr/bin/python

# Testing functions for the admetrics module.

import os
import sys
import codecs
import logging
import unittest
import subprocess
from StringIO import StringIO

from admetrics import AdInfo, AdDataReader, CSVError, CSVReader

class TestAdInfo(unittest.TestCase):
    """Unit tests for the AdInfo class"""

    REQUIRED_FIELDS = (
        'date', 'ad group', 'ad name', 'impressions', 'clicks', 'ctr', 'total cost')

    def setUp(self):
        self.did_warning = None

    def warnings(self, msg):
        self.did_warning = msg

    def make_ascii_adinfo(self,
            date='2012-01-01',
            ad_group='dummy group',
            ad_name='dummy name',
            impressions='8',
            clicks='2',
            ctr='0.25',
            total_cost='$100.00'):
        """Utility function for generating ascii data AdInfo objects"""

        info = AdInfo(self.warnings, self.REQUIRED_FIELDS, (
            date, ad_group, ad_name, impressions, clicks, ctr, total_cost))
        return info

    def make_unicode_adinfo(self,
            date=u'2012-01-01',
            ad_group=u'dummy group',
            ad_name=u'dummy name',
            impressions=u'8',
            clicks=u'2',
            ctr=u'0.25',
            total_cost=u'$100.00'):
        """Utility function for generating Unicode data AdInfo objects"""

        info = AdInfo(self.warnings, self.REQUIRED_FIELDS, (
            date, ad_group, ad_name, impressions, clicks, ctr, total_cost))
        return info

    def test_simple(self):
        """Test the creation of a simple AdInfo object"""

        info = self.make_ascii_adinfo()

        self.assertEqual(info.ad_group, 'dummy group')
        self.assertEqual(info.ad_name, 'dummy name')
        self.assertEqual(info.impressions, 8)
        self.assertEqual(info.clicks, 2)
        self.assertEqual(info.ctr, 0.25)
        self.assertEqual(info.total_cost, 100.0)
        self.assertIsNone(self.did_warning)

    def test_unicode(self):
        """Test the creation of a simple AdInfo object with Unicode data"""

        info = self.make_unicode_adinfo()

        self.assertEqual(info.ad_group, u'dummy group')
        self.assertEqual(info.ad_name, u'dummy name')
        self.assertEqual(info.impressions, 8)
        self.assertEqual(info.clicks, 2)
        self.assertEqual(info.ctr, 0.25)
        self.assertEqual(info.total_cost, 100.0)
        self.assertIsNone(self.did_warning)

    def test_bad_impressions(self):
        """Test sanity checking for invalid impressions/cost relationship"""

        with self.assertRaises(CSVError):
            info = self.make_ascii_adinfo(impressions='0')

    def test_empty_group(self):
        """Test sanity checking for non-empty group"""

        with self.assertRaises(CSVError):
            info = self.make_ascii_adinfo(ad_group='')

class TestAdDataReader(unittest.TestCase):
    """Unit tests for the AdDataReader class"""

    def setUp(self):
        self.click_total = 0

    def null_producer(self, ad_info, first, args):
        """A producer that does nothign"""

        pass

    def click_totaler_producer(self, ad_info, first, args):
        """A producer that tallies the clicks fields"""

        self.click_total += ad_info.clicks

    def date_check_producer(self, ad_info, first, args):
        """A producer that saves off the data files date value"""

        self.sample_date = ad_info.date

    def make_reader_from_sample(self, producer=None):
        """Return a reader for the sample input file"""

        if producer is None:
            producer = self.null_producer
        sample = open("sample_input.csv", "r")
        reader = AdDataReader(
            codecs.getreader("utf-8")(sample),
            producer,
            True)
        return reader

    def test_read_given_sample(self):
        """Try to read the sample data file we were given"""

        reader = self.make_reader_from_sample()
        self.assertIsNotNone(reader)
        reader.process_input()

    def test_reader_count_clicks(self):
        """Check for expected clicks in sample data file"""

        self.click_total = 0
        reader = self.make_reader_from_sample(producer=self.click_totaler_producer)
        reader.process_input()
        self.assertEqual(self.click_total, 167)

    def test_reader_verify_date(self):
        """Check sample data file for expected date"""

        self.sample_date = ""
        reader = self.make_reader_from_sample(producer=self.date_check_producer)
        reader.process_input()
        self.assertEqual(self.sample_date, u'2011-01-01')

class TestCSVReader(unittest.TestCase):
    """Tests for the CSVReader class"""

    def test_simple_csv(self):
        """Test basic CSV reading capabilities"""

        reader = CSVReader(StringIO("a,b,c\n"))
        values = reader.parse_line()
        self.assertEqual(values[0], "a")
        self.assertEqual(values[1], "b")
        self.assertEqual(values[2], "c")
        # End of input signaled by None
        next = reader.parse_line()
        self.assertIsNone(next)

    def test_value_trimming(self):
        """Verify that CSV fields are whitespace-trimmed"""

        reader = CSVReader(StringIO("a, b ,c\n"))
        values = reader.parse_line()
        self.assertEqual(values[1], "b")

    def test_reader_unicode(self):
        """Handle Unicode data via the CSV reader"""

        reader = CSVReader(StringIO(u"a,b,c\n"))
        values = reader.parse_line()
        self.assertEqual(values[0], u"a")

    def test_reader_quotes(self):
        """Test CSV reader basic quote handling"""

        reader = CSVReader(StringIO('a,"b c","d"\n'))
        values = reader.parse_line()
        self.assertEqual(values[0], "a")
        self.assertEqual(values[1], "b c")
        self.assertEqual(values[2], "d")

    def test_reader_embedded_quotes(self):
        """Test CSV reader handling of embedded quotes"""

        reader = CSVReader(StringIO('a,"b ""c""",d\n'))
        values = reader.parse_line()
        self.assertEqual(values[1], 'b "c"')

    def test_reader_skips_blank_lines(self):
        """CSV reader should skip blank lines"""

        reader = CSVReader(StringIO("\na,b,c\n \n1,2,3\n"))
        values = reader.parse_line()
        self.assertEqual(values[0], "a")
        values = reader.parse_line()
        self.assertEqual(values[0], "1")

class TestCommandLine(unittest.TestCase):
    """Test the command-line handling of the sample main() in admetrics"""

    SAMPLE_IN = "sample_input.csv"
    SAMPLE_OUT = "sample_output.csv"

    def get_sample_output(self):
        """Return the contents of the sample output file"""

        return open(self.SAMPLE_OUT, "r").read()

    def test_sample_data(self):
        """Run the command-line on sample data"""

        metrics_in = open(self.SAMPLE_IN, "r")
        p = subprocess.Popen(
            ["./admetrics.py", "--no-total-warning"],
            stdin=metrics_in,
            stdout=subprocess.PIPE,
            stderr=sys.stderr)
        data_out = p.stdout.read()
        p.stdout.close()
        sample_out = self.get_sample_output()
        self.assertTrue(len(sample_out) > 0)
        self.assertTrue(sample_out == data_out)

    def test_ascii_encoding(self):
        """Run the command-line in ascii mode"""

        p = subprocess.Popen(
            ["./admetrics.py", '--output-encoding=ascii', '--no-total-warning',
                self.SAMPLE_IN],
            stdout=subprocess.PIPE,
            stderr=sys.stderr)
        data_out = p.stdout.read()

        self.assertTrue('cheap used hondas' in data_out)

    def test_no_bom(self):
        """Run the command-line on sample data, but omit BOM"""
        
        metrics_in = open(self.SAMPLE_IN, "r")
        p = subprocess.Popen(
            ["./admetrics.py", '--no-total-warning'],
            stdin=metrics_in,
            stdout=subprocess.PIPE,
            stderr=sys.stderr)
        data_out = p.stdout.read()
        p.stdout.close()

        sample_out = self.get_sample_output()

        self.assertTrue(len(data_out) > 0)
        self.assertTrue(sample_out == data_out)

if __name__ == '__main__':
    unittest.main()
