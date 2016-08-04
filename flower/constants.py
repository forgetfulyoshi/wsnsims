""" World constants """

import math

MVC_SPEED = 1.0  # * uregeter / ureg.second
TRANSMISSION_RATE = 1.0  # * ureg.bit / ureg.second
MOVEMENT_COST = 0.1  # * ureg.joule / uregeter # J/m
COMMUNICATION_RANGE = 140.0  # * uregeter
ALPHA = math.pow(10, -7)  # * ureg.joule / uregeter
DELTA = 2
BETA = math.pow(10, -10)  # * ureg.joule / uregeter ** DELTA
HOLD_TIME = 1.0  # * ureg.second