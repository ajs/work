#!/usr/bin/python

import sys
import codecs
import unittest
import logging

from admetrics import AdInfo, AdDataReader, CSVError

class TestAdInfo(unittest.TestCase):
    """
    Unit tests for the AdInfo class
    """
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

    def setUp(self):
        self.click_total = 0

    def null_producer(self, ad_info, first=False):
        """A producer that does nothign"""

        pass

    def click_totaler_producer(self, ad_info, first=False):
        logging.debug("producer got clicks: " + str(ad_info.clicks))
        self.click_total += ad_info.clicks

    def make_reader_from_sample(self, producer=None):
        """Return a reader for the sample input file"""

        if producer is None:
            producer = self.null_producer
        sample = open("sample_input.csv", "r")
        reader = AdDataReader(codecs.getreader("utf-8")(sample), producer)
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

if __name__ == '__main__':
    unittest.main()
