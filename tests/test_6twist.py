"""
Test: 6_Twist layout — sectional interlocking simulation
=========================================================
Layout topology (from configs/6_Twist/):

    Block4==-|                  |-==Block1
             |                 |
    Block3==point1==Block2==point2==Block5

    - Block1: signal9<-|seg18==seg19==seg20|->signal10
    - Block2: signal3<-|seg5==seg6==seg7|->signal4
    - Block3: signal1<-|seg1==seg2==seg3|->signal2
    - Block4: signal7<-|seg14==seg15==seg16|->signal8
    - Block5: signal5<-|seg9==seg10==seg11|->signal6

    - point1(seg4):  stem->seg5  normal->seg3  reverse->seg16
    - point2(seg8):  stem->seg9  normal->seg7  reverse->seg18

Routes:
    - r0 (UP):   signal2->signal4   path=[point1, seg5, seg6, seg7]     point1=NORMAL
    - r1 (DOWN): signal3->signal1   path=[point1, seg3, seg2, seg1]     point1=NORMAL
    - r2 (DOWN): signal3->signal7   path=[point1, seg16, seg15, seg14]  point1=REVERSE
    - r3 (UP):   signal4->signal10  path=[point2, seg18, seg19, seg20]  point2=REVERSE
    - r4 (UP):   signal4->signal6   path=[point2, seg9, seg10, seg11]   point2=NORMAL
    - r5 (DOWN): signal5->signal3   path=[point2, seg7, seg6, seg5]     point2=NORMAL
    - r6 (UP):   signal8->signal4   path=[point1, seg5, seg6, seg7]     point1=REVERSE
    - r7 (DOWN): signal9->signal3   path=[point2, seg7, seg6, seg5]     point1=REVERSE

Scenario:
--------
1. Train #1 - Route r0 (UP):   starts at seg3.occUp   -> destination seg7.occUp
   Train #2 - Route r2 (DOWN): starts at seg5.occDown -> destination seg14.occDown

2. Train #1 - Route r6 (UP):   starts at seg16.occUp    -> destination seg7.occUp
   Train #2 - Route r1 (DOWN): starts at seg5.occDown -> destination seg1.occDown

Note: pairs r3+r5 and r4+r7 are NOT included. Both rely on routes that enter
point2 via the NS face going DOWN (the channel-flip case in process_train_movement).
The block2 / block5 swap workaround used in 3_Cross cannot be composed here
because it would break the UP routes r0/r6/r3 that also traverse block2 in
their normal channels. These pairs need the underlying movement-layer fix.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from runner import TestScenario, TrainGoal, print_result, run_scenario
from entity import ElementOcc

# ---------------------------------------------------------------------------
# Scenario UP: r0 (anticlockwise, point1 NORMAL) — seg3.occUp -> seg7.occUp
# ---------------------------------------------------------------------------
SCENARIO_UP = TestScenario(
    layout='6_Twist',
    name='r0 UP (point1=NORMAL, seg3 -> seg7)',
    trains={
        'seg3': {'occUp': ElementOcc.COMPLETETRAINOCC},
    },
    routes=['r0'],
    goals=[
        TrainGoal('seg7', 'occUp'),
    ],
    max_steps=30,
)

# ---------------------------------------------------------------------------
# Scenario DOWN: r1 (clockwise, point1 NORMAL) — seg5.occDown -> seg1.occDown
# ---------------------------------------------------------------------------
SCENARIO_DOWN = TestScenario(
    layout='6_Twist',
    name='r1 DOWN (point1=NORMAL, seg5 -> seg1)',
    trains={
        'seg5': {'occDown': ElementOcc.COMPLETETRAINOCC},
    },
    routes=['r1'],
    goals=[
        TrainGoal('seg1', 'occDown'),
    ],
    max_steps=30,
)

# ---------------------------------------------------------------------------
# Scenario: Train #1 (r0: UP->seg7) + Train #2 (r2: DOWN->seg14)
# ---------------------------------------------------------------------------
# 1. Train #1 - Route r0 (UP):   starts at seg3.occUp   -> destination seg7.occUp
#    Train #2 - Route r2 (DOWN): starts at seg5.occDown -> destination seg14.occDown
# ---------------------------------------------------------------------------
SCENARIO_TWIST_1 = TestScenario(
    layout='6_Twist',
    name='Train #1 (r0: UP->seg7) + Train #2 (r2: DOWN->seg14)',
    trains={
        'seg3': {'occUp': ElementOcc.COMPLETETRAINOCC},  # Train #1 waits at signal2
        'seg5': {'occDown': ElementOcc.COMPLETETRAINOCC},  # Train #2 waits at signal3
    },
    routes=['r0', 'r2'],
    goals=[
        TrainGoal('seg7', 'occUp'),
        TrainGoal('seg14', 'occDown'),
    ],
    neighbor_corrections={},
    signal_corrections={},
    max_steps=30,
)

# ---------------------------------------------------------------------------
# Scenario: Train #1 (r6: UP->seg7) + Train #2 (r1: DOWN->seg1)
# ---------------------------------------------------------------------------
# 4. Train #1 - Route r6 (UP):   starts at seg16.occUp    -> destination seg7.occUp
#    Train #2 - Route r1 (DOWN): starts at seg5.occDown -> destination seg1.occDown
# ---------------------------------------------------------------------------
SCENARIO_TWIST_2 = TestScenario(
    layout='6_Twist',
    name='Train #1 (r6: UP->seg7) + Train #2 (r1: DOWN->seg1)',
    trains={
        'seg16': {'occUp': ElementOcc.COMPLETETRAINOCC},  # Train #1 waits at signal8
        'seg5': {'occDown': ElementOcc.COMPLETETRAINOCC},  # Train #2 waits at signal3
    },
    routes=['r6', 'r1'],
    goals=[
        TrainGoal('seg7', 'occUp'),
        TrainGoal('seg1', 'occDown'),
    ],
    neighbor_corrections={},
    signal_corrections={},
    max_steps=30,
)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    passed = True
    for scenario in (SCENARIO_UP, SCENARIO_DOWN,
                     SCENARIO_TWIST_1, SCENARIO_TWIST_2):
        result = run_scenario(scenario)
        print_result(scenario, result)
        if not result['passed']:
            passed = False
    sys.exit(0 if passed else 1)
