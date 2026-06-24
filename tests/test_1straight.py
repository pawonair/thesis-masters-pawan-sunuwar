"""
Test: 1_Straight layout — sectional interlocking simulation
============================================================
Layout topology (from configs/1_Straight/):

        |seg1===seg2===seg3==|==seg5===seg6===seg7|
    (signal1)        (signal2│signal3)        (signal4)

    - Block3: seg1, seg2, seg3  (signals: signal1 at seg1.down, signal2 at seg3.up)
    - Block2: seg5, seg6, seg7  (signals: signal3 at seg5.down, signal4 at seg7.up)
    - No points. Two independent routes on a single straight track.

Routes:
    - r0 (UP/anticlockwise): signal2 -> signal4,  path=[seg5, seg6, seg7]
    - r1 (DOWN/clockwise)  : signal3 -> signal1,  path=[seg3, seg2, seg1]

*r0 and r1 share the same physical track so they CONFLICT and must run in separate scenarios.

Signal / neighbor assignments (parser output, no corrections needed):
    - seg3.up_signal     = signal2   (guards UP exit from block3 into block2)
    - seg3.up_neighbor   = seg5      (wired by configure_remaining_neighbors for r0)
    - seg5.down_signal   = signal3   (guards DOWN exit from block2 into block3)
    - seg5.down_neighbor = seg3      (wired by configure_remaining_neighbors for r1)
    - seg7.up_signal     = signal4   (terminal guard, train stays at seg7)
    - seg1.down_signal   = signal1   (terminal guard, train stays at seg1)

Scenarios:
---------
Each direction is run independently:
1. Scenario UP (r0): train at seg3.occUp -> destination seg7.occUp
    Train waits at signal2 (seg3.up_signal). Once r0 is LOCKED and signal2=GO,
    the train advances: seg3 -> seg5 -> seg6 -> seg7. Arrives in 6 steps.

2. Scenario DOWN (r1): train at seg5.occDown -> destination seg1.occDown
    Train waits at signal3 (seg5.down_signal). Once r1 is LOCKED and signal3=GO,
    the train advances: seg5 -> seg3 -> seg2 -> seg1. Arrives in 6 steps.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from runner import TestScenario, TrainGoal, print_result, run_scenario
from entity import ElementOcc

# ---------------------------------------------------------------------------
# Scenario UP: r0 (anticlockwise) — seg3.occUp -> seg7.occUp
# ---------------------------------------------------------------------------
SCENARIO_UP = TestScenario(
    layout='1_Straight',
    name='r0 UP (seg3 -> seg7)',
    trains={
        'seg3': {'occUp': ElementOcc.COMPLETETRAINOCC},
    },
    routes=['r0'],
    goals=[
        TrainGoal('seg7', 'occUp'),
    ],
    max_steps=20,
)

# ---------------------------------------------------------------------------
# Scenario DOWN: r1 (clockwise) — seg5.occDown -> seg1.occDown
# ---------------------------------------------------------------------------
SCENARIO_DOWN = TestScenario(
    layout='1_Straight',
    name='r1 DOWN (seg5 -> seg1)',
    trains={
        'seg5': {'occDown': ElementOcc.COMPLETETRAINOCC},
    },
    routes=['r1'],
    goals=[
        TrainGoal('seg1', 'occDown'),
    ],
    max_steps=20,
)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    passed = True
    for scenario in (SCENARIO_UP, SCENARIO_DOWN):
        result = run_scenario(scenario)
        print_result(scenario, result)
        if not result['passed']:
            passed = False
    sys.exit(0 if passed else 1)
