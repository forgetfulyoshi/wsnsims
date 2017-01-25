
def much_greater_than(lhs, rhs, r=0.2):
    """
    Determine if lhs >> rhs

    :param lhs: Left side of the comparison
    :param rhs: Right side of the comparison
    :param r: Ratio to use for comparison
    :returns True: If the ratio of lhs-to-rhs < r
    :returns False: Otherwise
    :rtype: bool
    """
    if rhs / lhs < r:
        return True

    return False
