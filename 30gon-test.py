#!/usr/bin/env python

# Generate the dataset used in John Baez's posting here:
# https://plus.google.com/u/0/117663015413546257905/posts/bPCvcDTDysi

import pprint
import logging
import itertools


def digitsin(t):
    return itertools.chain(*t)

def unique(l):
    alle = set([])
    for e in l:
        if e in alle:
            return False
        alle.add(e)
    return True

def listinlist(l1, l2):
    return repr(l1) in (repr(e) for e in l2)


logging.basicConfig(level=logging.INFO)
#logging.basicConfig(level=logging.DEBUG)

digits = range(6)
pairs = [list(x) for x in itertools.combinations(digits, 2)]
trips = [list(x) for x in itertools.combinations(pairs, 3) if unique(digitsin(x))]

total = len(pairs) + len(trips)
atpos = [[] for _ in range(total)]
posind = [0 for _ in range(total)]
all = []

i = 0
while i < total:
    parity = i % 2
    if parity == 0:
        source = trips
    else:
        source = pairs

    if posind[i] == 0:
        curlist = list(itertools.islice(all, parity, i, 2))
        atpos[i] = [ e for e in source if not listinlist(e, curlist) ]
        posind[i] = 0

    if posind[i] >= len(atpos[i]):
        atpos[i] = []
        posind[i] = 0
        i -= 1
        continue

    logging.debug("Step: %r" % [ posind[e] for e in range(i) ])
    cur = atpos[i][posind[i]]
    posind[i] += 1

    if parity == 0 and i != 0:
        curpair = all[i-1]
        curtrip = cur
    elif parity == 1:
        curpair = cur
        curtrip = all[i-1]
    if i == 0 or listinlist(curpair, curtrip):
        all = all[0:i] + [cur]
        i += 1

print "Resulting structure: %r" % (all,)
