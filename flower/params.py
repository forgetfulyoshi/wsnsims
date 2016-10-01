""" World constants """

import math

# Parameters as specified in the paper
GRID_WIDTH = 1200  # meters
GRID_HEIGHT = 1200  # meters
COMMUNICATION_RANGE = 100 # 200.0 # meters
SEGMENT_COUNT = 12  # 20
MDC_COUNT = 5  # 5
ISDVA = 45  # Mbits
ISDVSD = 3
MOVEMENT_COST = 1  # Joule / meter
INITIAL_ENERGY = 100000  # Joule
MDC_SPEED = 0.1  # meter / second
TRANSMISSION_RATE = 0.1  # Mbit / sec

# Used in transmission energy calculations
ALPHA = math.pow(10, -7)  # * ureg.joule / ureg.meter
DELTA = 2
BETA = math.pow(10, -10)  # * ureg.joule / ureg.meter ** DELTA
COMMS_COST = 2  # Joule / Mbit

# Used in setting up the simulation
DAMAGE_RADIUS = 100
NOT_CLUSTERED = -1
