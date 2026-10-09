import random
import sys

### hw_1b

filename = sys.argv[1]

with open(filename) as f:
    for line in f:
        if random.random() < 0.01:
            print(line, end="")

