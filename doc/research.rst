===============================
WSNSims Research Project Report
===============================
:Author: Ben Anglin
:Organization: University of Maryland, Baltimore County
:Date: December 2016
:Version: 1.0.0
:Contact: jama1@umbc.edu

Objective
=========
The purpose of this research is to compare FLOWER, an algorithm for re-establishing communication in a damaged (partitioned) wireless sensor network, to existing solutions. In particular, FLOWER is compared against ToCS (Touring of Clustered Segments). Metrics used for comparison include the average inter-segment communication latency, the energy use of mobile nodes, and the balance of energy use overall. Metrics are gathered through the use of simulations of each algorithm.

Both algorithms take the approach of using mobile nodes to relay data between clusters of network segments. At a high level, ToCS optimizes solely for the length of the tour made by a mobile node, while FLOWER also considers communication latency and energy requirements. 

Goals
=====
The primary goal of this research is to empirically demonstrate the performance of FLOWER as compared to ToCS. By using Markov simulation, we are able to demonstrate with 90% certainty the improvements made by FLOWER over ToCS.

An additional goal is to provide an extensible platform for use in future simulations and research. Initial work on this project included extensive searches for existing implementations of ToCS or other WSN algorithms, but none were found. As a result, all source code used in this project is published to GitHub [GH]_ and documented on ReadTheDocs [RTD]_ so as to serve as a resource for future research.

Further research will also be done to compare FLOWER to MINDS [MINDS]_ and FOCUS [FOCUS]_, which also provide solutions to the connectivity restoration problem. These implementations were initially slated to be included in this paper, but due to time constraints, they have be rescheduled to follow-on work.

Solution
========
To fully simulate both FLOWER and ToCS a few methods were explored. The first attempt was to use the ns-3 [ns3]_ network simulation framework. This framework is designed to build simulations of arbitrary network topologies and is incredibly powerful. Unfortunately, it comes with a very steep learning curve and minimal "out-of-the-box" support for sensor network simulation. After approximately one month of working with ns-3, it was abandoned in favor of a bespoke Python implementation.

The initial implementation of ToCS and FLOWER was written in pure Python 3.5. To accomplish this, a simple linear algebra library was compiled with support for some basic computational geometry routines such as convex-hull-finding using the "Graham Scan" method from CLRS [CLRS]_.

As the core purpose of any of the connectivity restoration algorithms is to produce a set of tours that will be traversed by mobile nodes. This requires the implementation of at least one Traveling Salesman algorithm. For these simulations, the implementation described in IDM-kMDC [IDM]_ was used. This method works by first finding the convex hull over the set of points to be visited by a mobile node. Once this is done, all interior points are added to the tour by finding the closest existing edge for each, and inserting the interior point, removing the original edge and creating two new ones.

.. INSERT IMAGES HERE  



Architecture
============
In order to simulate the behavior of FLOWER and ToCS, a program was developed to generate random damaged network layouts and run the algorithms against them. Because FLOWER borrows from ToCS for basic clustering logic, much of the code for the two can be shared. In addition generating networks, the program itself contains implementations of both ToCS and FLOWER in addition to the Traveling Salesman approach used by IDM-kMDC [IDM]_.

ToCS
----
The ToCS implementation is based directly upon the descriptions and diagrams from its paper. The algorithm begins by establishing a new "cluster" for each segment in the damaged network. The clusters are then merged in rounds until the number of clusters is equal to the number of available MDCs-1, the last MDC is reserved for use in the central cluster and handles inter-cluster data delivery. When two clusters are merged, all of their respective segments are joined into a single cluster. In order to establish which clusters are merged during each round, the following cost equation is used [ToCS]_,

    f_ij = Tour(C_i+C_j+Centroid) - Tour(C_i+Centroid)

where C_i and C_j are the clusters in question, Centroid is the central cluster, and Tour() is defined as the length of the path an MDC will travel in order to visit each segment in a cluster. Note that Tour(C_i + C_j) != Tour(C_i) + Tour(C_j) as there is almost always additional travel distance between groups of segments. The pair of clusters with the lowest cost is selected for merging.

FLOWER
------
The implementation of FLOWER closely follows the psuedocode provided in its appendix in an attempt to capture the author's intentions as closely as possible. Some deviations were made where necessary, but only to ensure correctness of the algorithm.

FLOWER begins by superimposing a 2D grid on top of the damaged network. This grid is composed of square cells with sides of length R / sqrt(2), where R is the communication range of the MDCs and segments (MDCs and segments are assumed to have the same radio range). Once this grid is formed, cells are identified that are within radio range of segments.  

FLOWER's initial clustering phase is very similar to ToCS. 

Maximum inter-segment data delivery latency
-------------------------------------------


Energy balance among MDCs
-------------------------
(Discuss results)

Average energy consumption of all MDCs
--------------------------------------
(Discuss results)

Previous Work
=============

Baseline Approaches
===================
The performance of FLOWER was compared to ToCS [ToCS]_. ToCS, like FLOWER, forms clusters of segments in a star topology and balances tour lengths of MDCs. This provides a natural comparison for FLOWER as it builds upon the tour length balancing of ToCS and introduces communication balancing.

Simulation Results
==================
Implementations of FLOWER and ToCS were created in Python. In both cases, the simulation begins by laying out a grid of cells. The size of the cells are determined by the communication range and the overall size of the grid is adjusted to ensure that there are no partial cells.

Once the grid and cells have been initialized, the center of the grid is selected as the "damaged area" with a configurable damage radius (default is 100 meters). At this point, segments are randomly placed anywhere on the grid outside of the damaged area.

For the FLOWER simulation, cell, virtual cluster, and cluster creation are performed as per [FLOWER]_. Likewise, the ToCS simulation follows the steps of [ToCS]_. Because both FLOWER and ToCS leverage the same approach for path finding, much of their underlying implementation is shared. For instance, a common 2-D vector library is used, along with a hull-finding algorithm (Graham Scan as described in [CLRS]_), path-finding algorithm (as in [IDM]_), and cluster merging algorithm as in [ToCS]_.

The result of both implementation is a set of data that contains cluster, tour, and energy data. This data is then used to calculate each of the performance metrics. All source code for the simulations is available on GitHub at https://github.com/forgetfulyoshi/wsnsims

For our simulations, we have used the following sets of parameters

- Number of segments:       [12, 15, 18, 21, 24, 30]
- Number of MDCs:           [3, 5, 7, 9]
- Radio ranges (meters):    [50, 70, 100, 150, 200]
- ISDVa values (Mbits):     [45]
- ISDVsd values:            [0.0, 3.0]

All other elements were held constant as follows:

- Area of interest:         1200 meters x 1200 meters
- Energy for motion:        1 Joule/meter
- Energy for communication: 2 Joule/Mbit
- Initial MDC energy:       1000 Joule
- MDC Speed:                0.1 meter/second
- Wireless bandwidth:       0.1 Mbps

Maximum inter-segment data delivery latency
-------------------------------------------
(Discuss results)

Energy balance among MDCs
-------------------------
(Discuss results)

Network lifetime
----------------
(Discuss results)

Average energy consumption of all MDCs
--------------------------------------
(Discuss results)

Buffer space required at gateway segments
-----------------------------------------
(Discuss results)


References
----------

.. [FLOWER] S. Lee et. al., "Load and Resource Aware Federation of Multiple Sensor Network Segments," UMBC, Baltimore, MD, 2016.

.. [ToCS] J. L. V. M. Stanislaus and M. Younis, "Mobile Relays Based Federation of Multiple Wireless Sensor Network Segments with Reduced-latency," in IEEE ICC 2013 - Wireless Networking Symp., 2013, pp. 5000-5004.
 
.. [CLRS] Cormen et. al., Introduction to Algorithms, Cambridge, MA: The MIT Press, 2009, ch. 33, sec. 3, pp. 1030-1036. 

.. [IDM] F. Senel and M. Younis, "Optimized Interconnection of Disjoint Wireless Sensor Network Segments Using K Mobile Data Collectors," in IEEE ICC 2012 - Proc. of Int. Conf. on Communication, Ottawa, Canada, 2012, pp. 497-501.

.. [MINDS]

.. [FOCUS]