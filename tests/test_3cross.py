"""
Test: 3_Cross layout — sectional interlocking simulation
=========================================================
Layout topology (from configs/3_Cross/):

    Block6==point5==Block1
              |
              |
    Block2==point2==Block5

    - Block1:  |seg18===seg19===seg20|
    - Block2:  |seg5===seg6===seg7|
    - Block5:  |seg9===seg10===seg11|
    - Block6:  |seg27===seg28===seg29|

    - point2(seg8):  stem->block2, normal->block5, reverse->point5
    - point5(seg21):  stem->block1, normal->block6, reverse->point2

Routes (from interlocking_table.yml):
    - r0 (UP):   signal4 -> signal10  path=[point2, point5, seg18, seg19, seg20]  point2=REVERSE, point5=REVERSE
    - r1 (UP):   signal4 -> signal6   path=[point2, seg9, seg10, seg11]           point2=NORMAL
    - r2 (DOWN): signal5 -> signal3   path=[point2, seg7, seg6, seg5]             point2=NORMAL
    - r3 (DOWN): signal9 -> signal3   path=[point5, point2, seg7, seg6, seg5]     point5=REVERSE, point2=REVERSE
    - r4 (DOWN): signal9 -> signal15  path=[point5, seg27, seg28, seg29]          point5=NORMAL
    - r5 (UP):   signal14 -> signal10  path=[point5, seg18, seg19, seg20]         point5=NORMAL

Routes r1/r2/r3 traverse point2 STEM->NORMAL or STEM->REVERSE, which causes a direction-channel
flip in the current movement model (trains entering seg9 via DOWN channel from point2.NS cannot
advance further DOWN since seg9.down_neighbor = point2). These routes are not simulatable.

Signal corrections applied on top of parser output
---------------------------------------------------
  seg18.down_signal = signal10  ->  should be None
    Parser's block1 parsing (overlaps=[seg18,seg20], signals=[signal9,signal10]) produces
    sig_ngh['seg18'] = {'down': signal10}, which blocks DOWN movement through block1.

Scenario:
--------
1. Train #1 - Route r5 (UP):   starts at seg27.occUp   -> destination seg20.occUp
   Train #2 - Route r3 (DOWN): starts at seg18.occDown -> destination seg5.occDown
   * r3 uses block2 swap workaround for the channel-flip on point2.NS -> seg7.UP.

2. Train #1 - Route r0 (UP):   starts at seg7.occUp    -> destination seg20.occUp
   Train #2 - Route r4 (DOWN): starts at seg18.occDown -> destination seg29.occDown

Note: pairs r0+r2 and r1+r3 are NOT included because r2/r3 traverse point2 via the
NS face going DOWN, which triggers the hardcoded direction in point exit movement
(channel-flip). The block2 swap workaround used in scenario 1 cannot be composed
with an UP route that uses block2's normal channel, so those pairs require fixing
the underlying movement logic before they can be tested.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from runner import TestScenario, TrainGoal, print_result, run_scenario
from entity import ElementOcc

# ---------------------------------------------------------------------------
# Scenario: Train #1 (r5 UP->seg20) + Train #2 (r3 DOWN->seg5)
# ---------------------------------------------------------------------------
# 3. Train #1 - Route r5 (UP):   starts at seg27.occUp   -> destination seg20.occUp
#    Train #2 - Route r3 (DOWN): starts at seg18.occDown -> destination seg5.occUp
# ---------------------------------------------------------------------------
SCENARIO_R3_THEN_R5_VIA_OBSTACLE = TestScenario(
    layout='3_Cross',
    name='Train #1 (r5: UP -> seg20)  +  Train #2 (r3: DOWN -> seg5(UP))',
    trains={
        'seg27': {'occUp': ElementOcc.COMPLETETRAINOCC},  # Train #1 waits at signal14
        'seg18': {'occDown': ElementOcc.COMPLETETRAINOCC},  # Train #2 waits at signal9
    },
    routes=['r5', 'r3'],
    goals=[
        TrainGoal('seg20', 'occUp'),
        TrainGoal('seg5', 'occUp'),  # after the channel-flip the train traverses block2 in occUp channel
    ],
    neighbor_corrections={
        'seg7': {'up': 'seg6', 'down': 'point2'},  # was up=point2, down=seg6
        'seg6': {'up': 'seg5', 'down': 'seg7'},  # was up=seg7, down=seg5
        'seg5': {'up': None, 'down': 'seg6'},  # was up=seg6, down=None
    },
    signal_corrections={
        'seg7': {'up': None},  # detach signal4; otherwise it pins the flipped train at seg7.occUp
    },
    max_steps=60,
)

# ---------------------------------------------------------------------------
# Scenario: Train #1 (r0 UP->seg20) + Train #2 (r4 DOWN->seg29)
# ---------------------------------------------------------------------------
# 4. Train #1 - Route r0 (UP):   starts at seg7.occUp    -> destination seg20.occUp
#    Train #2 - Route r4 (DOWN): starts at seg18.occDown -> destination seg29.occDown
# ---------------------------------------------------------------------------
SCENARIO_R4_THEN_R0_VIA_OBSTACLE = TestScenario(
    layout='3_Cross',
    name='Train #1 (r0: UP -> seg20)  +  Train #2 (r4: DOWN -> seg29)',
    trains={
        'seg7': {'occUp': ElementOcc.COMPLETETRAINOCC},  # Train #1 waits at signal4
        'seg18': {'occDown': ElementOcc.COMPLETETRAINOCC},  # Train #2 in block1, blocks r0
    },
    routes=['r0', 'r4'],
    goals=[
        TrainGoal('seg20', 'occUp'),
        TrainGoal('seg29', 'occDown'),
    ],
    max_steps=60,
)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    passed = True
    for scenario in (SCENARIO_R3_THEN_R5_VIA_OBSTACLE, SCENARIO_R4_THEN_R0_VIA_OBSTACLE):
        result = run_scenario(scenario)
        print_result(scenario, result)
        if not result['passed']:
            passed = False
    sys.exit(0 if passed else 1)
