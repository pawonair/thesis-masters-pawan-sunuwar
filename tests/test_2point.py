"""
Test: 2_Point layout — sectional interlocking simulation
=========================================================
Layout topology (from configs/2_Point/):

    |seg1===seg2===seg3|===point1(seg4)===|seg5===seg6===seg7|
                             |
       |seg14===seg15===seg16|

    - point1(seg4):  stem->seg5, normal->seg3, reverse->seg16

Routes:
    - r0 (UP):   signal2 -> signal4,  path=[point1, seg5, seg6, seg7],  point1=NORMAL
    - r1 (DOWN): signal3 -> signal1,  path=[point1, seg3, seg2, seg1],  point1=NORMAL
    - r2 (DOWN): signal3 -> signal7,  path=[point1, seg16,seg15,seg14], point1=REVERSE
    - r3 (UP):   signal8 -> signal4,  path=[point1, seg5, seg6, seg7],  point1=REVERSE

Signal corrections applied on top of parser output
---------------------------------------------------
After the parser fix, block2 [signal3,signal4] correctly assigns seg7.up=signal4.
Two corrections remain necessary:
1. seg5.down_signal = signal3  ->  should be None
    (parser places signal3 at the stem overlap, but the route entry is at seg6)
2. seg6.down_signal = None     ->  should be signal3
    (signal3 must be at seg6 so configure_remaining_neighbors connects seg6->point1
    and the DOWN train in seg6 waits at signal3 before route LOCKED)

Scenarios:
---------
Two non-conflicting routes are tested in one run:
1. Train #1 - Route r0 (UP):   starts at seg3.occUp   -> destination seg7.occUp
   Train #2 - Route r2 (DOWN): starts at seg6.occDown -> destination seg14.occDown

   *Train #2 must traverse point1 first (point1 starts NORMAL; r2 commands REVERSE).
   Once Train #2 clears point1, r0 can allocate and Train #1 proceeds.

2. Train #1 - Route r1 (DOWN): starts at seg5.occDown -> destination seg1.occDown
   Train #2 - Route r3 (UP):   starts at seg16.occUp -> destination seg7.occUp

   * Train #1 must traverse point1 first (point1 starts NORMAL; r1 requires NORMAL).
   Once Train #1 clears point1, r3 can allocate and Train #2 proceeds.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from runner import TestScenario, TrainGoal, print_result, run_scenario
from entity import ElementOcc

# ---------------------------------------------------------------------------
# Signal corrections: fix parser mis-assignments for 2_Point
# ---------------------------------------------------------------------------
_SIGNAL_CORRECTIONS = {
    'seg5': {'down': 'signal3'},  # parser puts signal3 at stem overlap; entry is at seg6
    'seg6': {'down': None},  # signal3 guards DOWN exit from block2 into point1
}

# ---------------------------------------------------------------------------
# Scenario: Train #1 (r0 UP->seg7) + Train #2 (r2 DOWN->seg14)
# ---------------------------------------------------------------------------
SCENARIO_TWO_TRAINS_1 = TestScenario(
    layout='2_Point',
    name='Train #1 (r0: UP -> seg7)  +  Train #2 (r2: DOWN -> seg14)',
    trains={
        'seg3': {'occUp': ElementOcc.COMPLETETRAINOCC},  # Train #1 waits at signal2
        'seg6': {'occDown': ElementOcc.COMPLETETRAINOCC},  # Train #2 waits at signal3
    },
    routes=['r0', 'r2'],
    goals=[
        TrainGoal('seg7', 'occUp'),  # Train #1 destination
        TrainGoal('seg14', 'occDown'),  # Train #2 destination
    ],
    max_steps=60,
)

# ---------------------------------------------------------------------------
# Scenario: Train #1 (r1 DOWN->seg1) + Train #2 (r3 UP->seg7)
# ---------------------------------------------------------------------------
SCENARIO_TWO_TRAINS_2 = TestScenario(
    layout='2_Point',
    name='Train #1 (r1: DOWN -> seg1)  +  Train #2 (r3: UP -> seg7)',
    trains={
        'seg5': {'occDown': ElementOcc.COMPLETETRAINOCC},  # Train #1 waits at signal2
        'seg16': {'occUp': ElementOcc.COMPLETETRAINOCC},  # Train #2 waits at signal3
    },
    routes=['r1', 'r3'],
    goals=[
        TrainGoal('seg1', 'occDown'),  # Train #1 destination
        TrainGoal('seg7', 'occUp'),  # Train #2 destination
    ],
    max_steps=60,
)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    passed = True
    for scenario in (SCENARIO_TWO_TRAINS_1, SCENARIO_TWO_TRAINS_2):
        result = run_scenario(scenario)
        print_result(scenario, result)
        if not result['passed']:
            passed = False
    sys.exit(0 if passed else 1)
