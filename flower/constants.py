""" World constants """

import math

MVC_SPEED = 6.0  # * ureg.meter / ureg.minute
TRANSMISSION_RATE = 1.0  # * ureg.bit / ureg.second
MOVEMENT_COST = 1  # * ureg.joule / ureg.meter # J/m
COMMUNICATION_RANGE = 100.0  # * ureg.meter
ALPHA = math.pow(10, -7)  # * ureg.joule / ureg.meter
DELTA = 2
BETA = math.pow(10, -10)  # * ureg.joule / ureg.meter ** DELTA
HOLD_TIME = 1.0  # * ureg.second
MDC_COUNT = 5
SEGMENT_COUNT = 18
DAMAGE_RADIUS = 200
NOT_CLUSTERED = -1
ISDVA = 10  # * ureg.mbit
ISDVSD = 0
