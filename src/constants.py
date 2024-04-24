"""
some constants used in the project
"""

from typing import Final
import numpy as np

APP_NAME = 'NN-XOR Study'
ORG_NAME = 'Some cute NN-XOR organization'

MODELS_DIR = 'models'

NBSP = '\xa0'

EPSILON = 1e-7
LEAKY_eps = 0.1

X_BATCH_4: Final[np.ndarray] = np.array(
    [[0, 0],
     [0, 1],
     [1, 0],
     [1, 1]]
     )

Y_XOR_TRUE_4: Final[np.ndarray] = np.array(
    [[0],
     [1],
     [1],
     [0]]
     )

MAX_LEN_FILENAME_JSON = 50

class CHOICES_LISTS:
    """ lists choices constants for General parameters"""
    BATCH_SIZE = [1, 2, 4, 10]
    EPOCH_SIZE = [100, 200, 500, 1000, 2000, 5000]
    CYCLES_PER_EPOCH = [1, 2, 5, 10]
    GRANULARITY = [1, 2, 5, 10, 20, 50, 100]

XOR_JSON_MODEL = "1.0"
XOR_JSON_SUPPORTED_MODELS = [XOR_JSON_MODEL]

