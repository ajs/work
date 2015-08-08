# A truly random number between 0 and 4

import os
import time
import random
import hashlib
import unittest
import numpy


# Several approaches to the problem: given f() returns a truly random
# number in the range 0-4, write a function that returns a uniformly
# random number in the range 0-6.


def _map_range(value, source_range, target_range):
    """
    Given a source range like 2**32, map a value from that
    range to a value in target range, e.g. 5. For best
    results (to minimize the impact of target_range not being
    a divisor of source_range, make sure that source_range is
    several orders of magnitude larger than target_range).
    """

    granularity = source_range // target_range
    if value > (granularity * target_range):
        return value % target_range
    else:
        return value // granularity

def _rand_n(target, bits=32):
    """
    Return an integer in the range 0 - `target`, non-inclusive,
    by extracting `bits` number of random bits from the system's
    random number generator (`/dev/urandom` under Linux) and then
    mapping the result to the target range. For uniformity, value of
    `2**bits` should either be at least a couple of orders of
    magnitude larger than `target` or equal to it.
    """

    if (bits % 8) != 0:
        raise ValueError("Must request multiple of 8 bits")
    if bits == 0:
        raise ValueError("Funny, wiseguy")

    n = os.urandom(bits//8)
    return _map_range(int(n.encode('hex'), 16), 2**bits, target)

def _rand5():
    """Our known random source of integers in range 0-4"""

    return _rand_n(5)

def _rand7():
    """Used for testing distribution of other functions"""

    return _rand_n(7)

def _populate_bits(func, source_bits, bits=16):
    """
    `func` is a function that returns an integer which occupies
    at most `source_bits` number of bits. Return an integer
    which is `bits` number of bits wide (or as close to as
    rounding will allow) comprised of multiple calls to `func`.

    No provision is made to cause the returned value to be
    at all uniform, and no expectation that it is should be
    made.
    """

    t = 0
    for i in range(0, (bits//source_bits)):
        t += func() << (bits*i)
    return t

def _populate_bits2(func, source_bits, bits=32):
    """
    Different strategy for some result as _populate_bits.
    """

    bits += 2

    shifts = bits - source_bits + 1
    if shifts <= 0:
        raise ValueError(
            "Bits requested is too small for %d bit input" % source_bits)
    t = 0
    for i in range(0, shifts):
        t ^= func() << i
    return ( (t >> 1) & (2**(bits-2)-1) )

def rand7by5_prng(prng=random.Random):
    """
    Given a PRNG, build a seed from our source and get an answer.

    This depends heavily on your PRNG having a very good uniformity
    for non-uniform seeds that contain sufficient entropy.
    Most modern PRNGs have this property, but just be aware that
    you are relying on this.
    """

    seed = _populate_bits(_rand5, source_bits=3)
    _prng = prng(seed)
    return _prng.randint(0, 6)

def rand7by5_prng2(prng=random.Random):
    seed = _populate_bits2(_rand5, source_bits=3)
    _prng = prng(seed)
    return _prng.randint(0, 6)

def rand7by5_hash(hashfunc=hashlib.md5, hashbits=128):
    """
    Given a hash function, build a string from our source, hash it
    and then normalize the hash as an integer to our range.

    Hashes need to have the property of each input bit having a
    uniform impact on each output bit (e.g. if input[x] is 1
    then there should be as close as possible to a 50% chance
    for any given bit in the output to be flipped vs. if input[x]
    were 0). Given this property, the result of this function
    will be uniform.
    """

    seed = _populate_bits2(_rand5, source_bits=3)
    hashed = hashfunc(str(seed)).digest()
    hexed = hashed.encode("hex")
    # Strip off high and low bit, which hashing functions might set
    # to 1 due to the ways hashes get used.
    shortbits = hashbits - 2
    shortrange = 2**shortbits
    stripped = (int(hexed, 16) >> 1) & (shortrange-1)
    return _map_range(stripped, shortrange, 7)

def rand7by5_lottery():
    """
    A datastructures approach.

    Run a lottery/horserace between every possible result value.
    The down side is that this requires enough memory for every
    value that could be returned, so that they can all be scored.
    Also, ties are resolved recursively, and so it's possible
    for this to run for an unbounded amount of time. In reality,
    the number of recursive calls should be relatively small,
    and the major performance hit will be the memory usage, but
    for 7 possible values, this is a fine approach.
    """

    def _winners(s, win):
        for i in range(len(s)):
            if s[i] >= win:
                yield i

    def _lottery(win, mapping=None):
        size = len(mapping)
        ordering = range(size)
        scores = [ 0 for _ in ordering ]
        while True:
            for i in ordering:
                scores[i] += _rand5()
            winners = list(_winners(scores, win))
            count = len(winners)
            if count == 1:
                return mapping[winners[0]]
            elif count > 1:
                # Resolve ties recursively
                return mapping[_lottery(win=win, mapping=winners)]

    return _lottery(win=20, mapping=range(7))

def rand7by5_modmap():
    """
    This is the simplest solution, but for very large target ranges,
    it will take quite a long time...

    Update:

    This is actually wrong... not by a lot, but it's wrong. The
    absolute distribution of all possible results is:

        0: 11172
        1: 11177
        2: 11172
        3: 11158
        4: 11144
        5: 11144
        6: 11158

    """

    t = 0
    for i in range(7):
        t += _rand5()
        t %= 7
    return t

def rand7by5_timing(bits=32, timing_checks=100):
    """Use timing on _rand5 to build an entropy pool"""

    # XXX We need to comb out the signal, here per RFC 4086
    t = 0
    for i in range(timing_checks):
        bit = i % bits
        start = time.time()
        _ = _rand5()
        end = time.time()
        delta = end - start
        assert delta != 0
        low = int(delta * 1000000) & 3 # low 2 bits of microseconds
        t ^= (low << bit) & (2**bits - 1)
    return _map_range(t, 2**bits, 7)


class RandTest(unittest.TestCase):
    """Unit tests for the above code, both internal and public interfaces"""

    # Number of times to call a random number function for testing
    trials = 10000

    def _random_coverage(self, func, size, *args, **kwargs):
        """Coverage of output of random number function"""

        seen = [0 for _ in range(size)]
        for _ in range(self.trials):
            n = func(*args, **kwargs)
            self.assertGreaterEqual(n, 0)
            self.assertLess(n, size)
            seen[n] += 1

        self.assertNotEqual(min(seen), 0, "Distribution is bad: %r" % (seen,))

        if size == 7:
            dev = numpy.std(seen)
            baseline_seen = [0 for _ in range(size)]
            for _ in range(self.trials):
                baseline_seen[_rand7()] += 1
            baseline_dev = numpy.std(baseline_seen)

            dev_ratio = abs(baseline_dev - dev)/baseline_dev

            #print "Differing by %.3f (%.3f base %.3f observed)" % (
            #    dev_ratio, baseline_dev, dev)

            self.assertTrue(
                dev < baseline_dev or dev_ratio < 0.5,
                "stddev: baseline %s; observed %s" % (baseline_dev, dev))

        return seen

    def _hist_coverage(self, name, hist):
        m = float(max(hist))
        print "%s histogram (max=%d %r):" % (name, m, hist)
        for i in range(len(hist)):
            stars = "".join(["*" for _ in range(int((hist[i]/m) * 61))])
            print "%-4d: %-60s" % (i, stars)

    def test_map_range(self):
        """Make sure we map ranges correctly"""

        self.assertEqual(_map_range(9, 15, 5), 3)
        self.assertEqual(_map_range(0, 2**32, 5), 0)
        self.assertEqual(_map_range(300, 2**32, 5), 0)

    def test_rand_n_10(self):
        """Coverage of output range for _rand_n(10)"""

        self._random_coverage(_rand_n, 10, 10)

    def test_rand5(self):
        self._random_coverage(_rand5, 5)

    def test_rand7by5_prng(self):
        hist = self._random_coverage(rand7by5_prng, 7)
        self._hist_coverage("rand7by5_prng", hist)

    def test_rand7by5_prng2(self):
        hist = self._random_coverage(rand7by5_prng2, 7)
        self._hist_coverage("rand7by5_prng2", hist)

    def test_rand7by5_hash(self):
        hist = self._random_coverage(rand7by5_hash, 7)
        self._hist_coverage("rand7by5_hash", hist)

    def test_rand7by5_lottery(self):
        hist = self._random_coverage(rand7by5_lottery, 7)
        self._hist_coverage("rand7by5_lottery", hist)

    def test_rand7by5_modmap(self):
        hist = self._random_coverage(rand7by5_modmap, 7)
        self._hist_coverage("rand7by5_modmap", hist)

    def test_rand7by5_timing(self):
        hist = self._random_coverage(rand7by5_timing, 7)
        self._hist_coverage("rand7by5_timing", hist)


if __name__ == '__main__':
    unittest.main()
