"""
Test: Full layout (SWTbahnLite) -- sectional interlocking simulation
====================================================================
Layout topology (from configs/Full/extras_config.yml + point_config.yml):

  Blocks:
    block1: seg18==seg19==seg20     signals=[signal10(UP), signal9(DOWN)]
    block2: seg5==seg6==seg7        signals=[signal4(UP),  signal3(DOWN)]
    block3: seg1==seg2==seg3        signals=[signal2(UP),  signal1(DOWN)]
    block4: seg14==seg15==seg16     signals=[signal8(UP),  signal7(DOWN)]
    block5: seg9==seg10==seg11      signals=[signal6(UP),  signal5(DOWN)]
    buffer: seg26                   signals=[signal13]
    platform1: seg27==seg28==seg29  signals=[signal14(UP), signal15(DOWN)]
    platform2: seg23==seg24==seg25  signals=[signal11(DOWN), signal12(UP)]

  Points:
    point1: seg=seg4, stem=seg5(block2.down), normal=seg3(block3.up),
            reverse=seg16(block4.up)
    point2: seg=seg8, stem=seg7(block2.up),  normal=seg9(block5.down),
            reverse=point5
    point3: seg=seg12, stem=seg11(block5.up), normal=seg1(block3.down),
            reverse=point4
    point4: seg=seg13, stem=seg14(block4.down), normal=point6,
            reverse=point3
    point5: seg=seg17, stem=seg18(block1.down), normal=seg27(platform1.up),
            reverse=point2
    point6: seg=seg21, stem=seg20(block1.up),  normal=point4,
            reverse=point7
    point7: seg=seg22, stem=seg23(platform2.up), normal=seg26(buffer),
            reverse=point6

Routes (75 total, r0-r74 -- relevant ones shown):
  r23 (DOWN): signal3 -> signal1  path=[point1, seg3, seg2, seg1]  point1=NORMAL
  r26 (DOWN): signal3 -> signal7  path=[point1, seg16, seg15, seg14]  point1=REVERSE
  r10 (DOWN): signal9 -> signal15 path=[point5, seg27, seg28, seg29]  point5=NORMAL

Parser issues found for Full
-----------------------------
1. UP SIGNAL STORED AS STRING NEIGHBOR: for overlap segments at the UP end of
   bidirectional blocks (seg7/block2, seg16/block4, seg20/block1), the parser
   sets up_neighbor to the signal name as a string (e.g., seg7.up_neighbor =
   'signal4') instead of setting up_signal. This breaks UP-direction movement
   through these segments: the train head cannot advance because the neighbor
   is a string, not a Linear or Point object.

   Affected segments: seg7 (up_nb='signal4'), seg16 (up_nb='signal8'),
                      seg20 (up_nb='signal10').

   NOT corrected here -- all chosen routes travel DOWN and do not use the UP
   terminal of block2, block4, or block1.

2. NO SIGNAL SWAP BUG: Unlike 7_Lite, extras_config.yml lists signals in
   [signal4, signal3] order for block2, so the parser correctly assigns
   signal3 to seg5.down_signal and 'signal4' to seg7.up_neighbor.
   All DOWN-direction signals are correctly placed; no signal_corrections
   needed.

Routes NOT simulatable in this test runner
------------------------------------------
  All UP routes whose last path segment has an up_neighbor stored as a string
  (instead of a Signal object or None): r2, r16-r21, r28-r38, r44-r52,
  r69-r74. Trains moving UP through the affected segments would try to advance
  to a string, causing a Python AttributeError or silent stall.

Scenario
--------
  Two non-conflicting interlocked routes run simultaneously:

  Train A (r23, DOWN): seg7.occDown -> seg1.occDown
    In block2 (main section), waiting at signal3 (seg5.down_signal).
    r23 goes MARKED -> ALLOCATING (step 1) -> LOCKED (step 2, signal3=GO,
    point1 already NORMAL) -> OCCUPIED (step 3, IS-EMPTY: point1.occSNR=FREE).
    Train A advances: seg7->seg6->seg5->point1(SNR->NS, NORMAL branch)->
    seg3->seg2->seg1. Arrives seg1.occDown=COMPLETETRAINOCC at step 7,
    blocked by signal1 (permanently STOP).

  Train B (r10, DOWN): seg19.occDown -> seg29.occDown  (platform1)
    In block1 (main section), waiting for signal9 (seg18.down_signal).
    r10 goes MARKED -> ALLOCATING (step 1) -> LOCKED (step 2, signal9=GO,
    point5 already NORMAL) -> OCCUPIED (step 3, IS-EMPTY: point5.occSNR=FREE).
    Train B advances: seg19->seg18->point5(SNR->NS, NORMAL branch)->
    seg27->seg28->seg29. Arrives seg29.occDown=COMPLETETRAINOCC at step 7,
    blocked by signal15 (permanently STOP, seg29 has no DOWN neighbor).

  r23 and r10 do NOT conflict (confirmed from interlocking table: 23 ∉
  r10.conflicts). Both routes lock at step 2 and complete at step 7.
  No obstacles, no signal corrections, no neighbor corrections required.

Both goals are met at step 7 with no safety violations.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from runner import TestScenario, TrainGoal, print_result, run_scenario
from entity import ElementOcc

# ---------------------------------------------------------------------------
# Scenario: Train A (r23 DOWN->seg1) + Train B (r10 DOWN->seg29 / platform1)
# ---------------------------------------------------------------------------
SCENARIO_FULL_1 = TestScenario(
    layout='Full',
    name='Train A (r23: DOWN -> seg1) via pt1.NORMAL  +  Train B (r10: DOWN -> seg29) via pt5.NORMAL -> platform1',
    trains={
        'seg7': {'occDown': ElementOcc.COMPLETETRAINOCC},  # Train A: in block2, waits at signal3
        'seg19': {'occDown': ElementOcc.COMPLETETRAINOCC},  # Train B: in block1, waits at signal9
    },
    routes=['r23', 'r10'],
    goals=[
        TrainGoal('seg1', 'occDown'),  # Train A destination (end of block3)
        TrainGoal('seg29', 'occDown'),  # Train B destination (end of platform1)
    ],
    max_steps=30,
)

# ---------------------------------------------------------------------------
# Scenario: Train #1 (r19: UP->seg7) + Train #2 (r26: DOWN->seg14)
# ---------------------------------------------------------------------------
# Canonical thesis pattern:
#   Train #1 - Route r19 (UP):   starts at seg2.occUp   -> destination seg7.occUp
#   Train #2 - Route r26 (DOWN): starts at seg6.occDown -> destination seg14.occDown
#
# r19 needs point1=NORMAL; r26 needs point1=REVERSE. r26 train's start segment
# (seg6) is in r19's path; r19 train's start (seg2) is not in r26's path. r26
# must run first; after it completes and releases point1, point1 reverses to
# NORMAL and r19 runs.
#
# Neighbor correction: the parser stores seg7.up_neighbor as the string
# 'signal4' (parser bug for block UP terminals), which would block r19's UP
# train from settling at seg7.occUp. Detaching it makes seg7 the UP terminal.
# ---------------------------------------------------------------------------
SCENARIO_FULL_R19_R26 = TestScenario(
    layout='Full',
    name='Train #1 (r19: UP->seg7) + Train #2 (r26: DOWN->seg14) via point1 reversal',
    trains={
        'seg2': {'occUp': ElementOcc.COMPLETETRAINOCC},  # Train #1 waits at signal2
        'seg6': {'occDown': ElementOcc.COMPLETETRAINOCC},  # Train #2 waits at signal3
    },
    routes=['r19', 'r26'],
    goals=[
        TrainGoal('seg7', 'occUp'),
        TrainGoal('seg14', 'occDown'),
    ],
    neighbor_corrections={'seg7': {'up': None}},
    signal_corrections={},
    max_steps=60,
)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    passed = True
    for scenario in (SCENARIO_FULL_1, SCENARIO_FULL_R19_R26):
        result = run_scenario(scenario)
        print_result(scenario, result)
        if not result['passed']:
            passed = False
    sys.exit(0 if passed else 1)
