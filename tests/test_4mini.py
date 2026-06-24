"""
Test: 4_Mini layout — sectional interlocking simulation
=========================================================
Layout topology (from configs/4_Mini/layout_diagram.dot):
    
                --==Block4==--
               |              \
    Block5==point3==Block3==point1==Block2
    
    - point1(seg4):  stem->block2(seg5),  normal->block3(seg3), reverse->block4(seg16)
    - point3(seg12): stem->block5(seg11), normal->block3(seg1), reverse->block4(seg14)

Routes (from interlocking_table.yml):
    - r0 (DOWN): signal1 -> signal5  path=[point3, seg11, seg10, seg9]  point3=NORMAL
    - r1 (UP):   signal2 -> signal4  path=[point1, seg5, seg6, seg7]    point1=NORMAL
    - r2 (DOWN): signal3 -> signal1  path=[point1, seg3, seg2, seg1]    point1=NORMAL
    - r3 (DOWN): signal3 -> signal7  path=[point1, seg16, seg15, seg14] point1=REVERSE
    - r4 (UP):   signal6 -> signal2  path=[point3, seg1, seg2, seg3]    point3=NORMAL
    - r5 (UP):   signal6 -> signal8  path=[point3, seg14, seg15, seg16] point3=REVERSE
    - r6 (DOWN): signal7 -> signal5  path=[point3, seg11, seg10, seg9]  point3=REVERSE
    - r7 (UP):   signal8 -> signal4  path=[point1, seg5, seg6, seg7]    point1=REVERSE

Scenario:
--------
1. Train #1 - Route r1 (UP):   starts at seg3.occUp   -> destination seg7.occUp
   Train #2 - Route r3 (DOWN): starts at seg5.occDown -> destination seg14.occDown

2. Train #1 - Route r2 (DOWN): starts at seg5.occDown -> destination seg1.occDown
   Train #2 - Route r7 (UP):   starts at seg16.occUp  -> destination seg7.occUp
   * Sequential conflict-serialization via point1 reversal:
     r2 (point1=NORMAL) allocates first (r7 cannot allocate while r2's train
     occupies seg5, which is in r7's path). After r2 completes and releases
     point1, point1 reverses to REVERSE and r7 runs.

Note: pairs using r0/r4/r5/r6 are NOT included because:
  - r0/r4 trigger an infinite movement loop at point3.NS (point3.normal=seg1
    leads back through point3 in this layout).
  - r5/r6 cannot move through point3.RS (point3.reverse='point4' is an
    unresolved string in 4_Mini's point_config). These routes are not
    simulatable until the underlying point-config or movement logic is fixed.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from runner import TestScenario, TrainGoal, print_result, run_scenario
from entity import ElementOcc

# ---------------------------------------------------------------------------
# Scenario: Train #1 (r1: UP->seg7) + Train #2 (r3: DOWN->seg14)
# ---------------------------------------------------------------------------
# 1. Train #1 - Route r1 (UP):   starts at seg3.occUp   -> destination seg7.occUp
#    Train #2 - Route r3 (DOWN): starts at seg5.occDown -> destination seg14.occDown
# ---------------------------------------------------------------------------
SCENARIO_MINI_1 = TestScenario(
    layout='4_Mini',
    name='Train #1 (r1: UP->seg7) + Train #2 (r3: DOWN->seg14)',
    trains={
        'seg3': {'occUp': ElementOcc.COMPLETETRAINOCC},  # Train #1 waits at signal2
        'seg5': {'occDown': ElementOcc.COMPLETETRAINOCC},  # Train #2 waits at signal3
    },
    routes=['r1', 'r3'],
    goals=[
        TrainGoal('seg7', 'occUp'),
        TrainGoal('seg14', 'occDown'),
    ],
    max_steps=30,
)

# ---------------------------------------------------------------------------
# Scenario: Train #1 (r2: DOWN->seg1) + Train #2 (r7: UP->seg7) — sequential
# ---------------------------------------------------------------------------
# 2. Train #1 - Route r2 (DOWN): starts at seg5.occDown -> destination seg1.occDown
#    Train #2 - Route r7 (UP):   starts at seg16.occUp  -> destination seg7.occUp
#
# r2 needs point1=NORMAL and r7 needs point1=REVERSE. r2's start segment (seg5)
# is in r7's path; r7's start (seg16) is not in r2's path. r2 must run first;
# after it completes and releases point1, point1 reverses and r7 runs.
# ---------------------------------------------------------------------------
SCENARIO_MINI_2 = TestScenario(
    layout='4_Mini',
    name='Train #1 (r2: DOWN->seg1) + Train #2 (r7: UP->seg7) via point1 reversal',
    trains={
        'seg5': {'occDown': ElementOcc.COMPLETETRAINOCC},  # Train #1 waits at signal3
        'seg16': {'occUp': ElementOcc.COMPLETETRAINOCC},  # Train #2 waits at signal8
    },
    routes=['r2', 'r7'],
    goals=[
        TrainGoal('seg1', 'occDown'),
        TrainGoal('seg7', 'occUp'),
    ],
    max_steps=60,
)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    passed = True
    for scenario in (SCENARIO_MINI_1, SCENARIO_MINI_2):
        result = run_scenario(scenario)
        print_result(scenario, result)
        if not result['passed']:
            passed = False
    sys.exit(0 if passed else 1)
