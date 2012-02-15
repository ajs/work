#!/usr/bin/python

#Utility functions:

import re
import sys
import logging

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
    if currency != "$":
        raise ValueError("TBD: No currency conversions available, yet")
    if len(s) == 1:
        raise ValueError("$ must be followed by numeric amount")
    value = s[1:]
    if re.match(CURRENCY_VALUE_RE, value):
        return string_to_float(value)
    else:
        raise ValueError("Currency value must be $d or $d.cc")

def AdInfo(object):
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

    def __init__(self, warner, ordering, csv, ctr_tolerance=3):
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
        self.ad_group = self.data['ad_group']
        self.ad_name = self.data['ad_name']
        self.impressions = string_to_integer(self.data['impressions'])
        self.clicks = string_to_integer(self.data['clicks'])
        ctr = string_to_float(self.data['ctr'])
        if self.impressions == 0:
            if ctr != 0:
                raise ValueError("Non-zero CTR for zero impressions: data corruption")
        else:
            if round(ctr, ctr_tolerance) != round(self.clicks/self.impressions):
                raise ValueError("Given CTR does not match clicks/impressions")
        self.total_cost = money_string_to_float(self.data['total_cost'])
        if self.total_cost == 0.0 and self.impressions > 0:
            self.warner("Sanity check failed: cost is zero for zero impressions")

class CSVReader(object):
    """A reader for the CSV input files"""
    def __init__(source=sys.stdin, destination=sys.stdout):
        """
        Initialize with the source of CSV input and the destination for output.
        Defaults to sys.stdin and sys.stdout, respectively.
        """

        self.source = source
        self.destination = destination


