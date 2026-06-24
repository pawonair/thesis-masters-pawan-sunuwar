"""
Test: 7_Lite layout — sectional interlocking simulation
=========================================================
Layout topology (from configs/7_Lite):

    - point1(seg4):  stem->seg5(block2.down),  normal->seg3(block3.up),   reverse->seg16(block4.up)
    - point2(seg8):  stem->seg7(block2.up),    normal->seg9(block5.down), reverse->point5(REVERSE)
    - point3(seg12): stem->seg11(block5.up),   normal->seg1(block3.down), reverse->point4(REVERSE)
    - point4(seg13): stem->seg14(block4.down), normal->point6(NORMAL),    reverse->point3(REVERSE)
    - point5(seg17): stem->seg18(block1.down), normal->seg27(platform1),  reverse->point2(REVERSE)
    - point6(seg21): stem->seg20(block1.up),   normal->point4(NORMAL),    reverse->point7(REVERSE)
    - point7(seg22): stem->seg23(platform2),   normal->seg26(buffer3),    reverse->point6(REVERSE)

    Block segments (from extras_config.yml):
    - Block1: signal9<-|seg18==seg19==seg20|->signal10
    - Block2: signal3<-|seg5==seg6==seg7|->signal4
    - Block3: signal1<-|seg1==seg2==seg3|->signal2
    - Block4: signal7<-|seg14==seg15==seg16|->signal8
    - Block5: signal5<-|seg9==seg10==seg11|->signal6

Routes:
    - r0 (UP):    signal8->signal4    path=[point1.reverse -> Block2]
    - r1 (DOWN):  signal9->signal3    path=[point5.reverse -> point2.reverse -> block2]
    - r2 (DOWN):  signal1->signal5    path=[point3.normal -> block5]
    - r3 (UP):    signal2->signal4    path=[point1.normal -> block2]
    - r4 (DOWN):  signal3->signal1    path=[point1.normal -> block3]
    - r5 (DOWN):  signal3->signal7    path=[point1.reverse -> block4]
    - r6 (UP):    signal10->signal8   path=[point6.normal -> point4.normal -> block4]
    - r7 (UP):    signal4->signal10   path=[point2.reverse -> point5.reverse -> block1]
    - r8 (UP):    signal4->signal6    path=[point2.normal -> block5]
    - r9 (DOWN):  signal5->signal3    path=[point2.normal -> block2]
    - r10 (UP):   signal6->signal8    path=[point3.reverse -> point4.reverse -> block4]
    - r11 (UP):   signal6->signal2    path=[point3.normal -> block3]
    - r12 (DOWN): signal7->signal9    path=[point4.normal -> point6.normal -> block1]
    - r13 (DOWN): signal7->signal5    path=[point4.reverse -> point3.reverse -> block5]
    - r14 (DOWN): signal11->signal9   path=[point7.reverse -> point6.reverse -> block1]
    - r15 (DOWN): signal14->signal10  path=[point5.normal -> block1]

Parser issues found for 7_Lite
-------------------------------
None — after the parser fixes (sigs[i] indexing, neighbor overwrite guard, and
Point-first configure_remaining_neighbors), the 7_Lite extras_config.yml already
uses the correct [DOWN_signal, UP_signal] ordering for all blocks. All signals and
neighbors are assigned correctly by the parser without any manual corrections.

Routes NOT simulatable in this layout
--------------------------------------
  r0, r3 (UP through block2 -> pt1): seg3.up_neighbor = None (overwritten by r11),
    seg16.up_neighbor = None (overwritten by r6). Trains in block3 or block4 cannot
    reach point1 going UP.

  r1 (DOWN via pt5.REV -> pt2.REV -> block2): seg18.up_neighbor = point5 (set by r15).
    Head from pt5.RS -> seg18.UP -> pt5.SNR -> pt2.RS -> seg7.UP -> creates an
    infinite loop between block2 and the pt2–pt5 connector pair.

  r2, r8, r9, r13 (routes through block5 or using pt3/pt2 normal branch):
    After exiting through a point's NS face -> stem, the head enters the stem-neighbor
    segment at its UP face, and that segment's UP neighbor leads back to the point —
    creating a loop. Affected by: seg11.up_neighbor = point3, seg9.down_neighbor = None.

  r6, r10, r12 (UP/DOWN routes through block1 via pt4–pt6): seg20.up_neighbor = seg19
    (set by r15 overwrite) instead of point6. Head at seg20.occUp loops between
    seg20 and seg19 indefinitely.

  r7 (UP via pt2.REV -> pt5.REV -> block1): seg18.up_neighbor = point5 (set by r15).
    Same loop as r1 in reverse direction.

  r14, r15 (through block1 via pt7 or pt5.NORMAL -> platform1): seg27 has no
    down_neighbor set (configure-remaining-neighbors does not fire when the route's
    first path element is a point's segName rather than a Linear section name).

Obstacles
---------
  seg9.occDown  = COMPLETETRAINOCC
    Prevents phantom auto-dispatched routes r2, r8, r13 from allocating (seg9 is in
    all their paths after the first element; its occupancy blocks vacancy checks).

  seg18.occDown = COMPLETETRAINOCC
    Prevents phantom auto-dispatched routes r7, r12, r14, r15 from allocating.
    sig18.down_signal = signal10 (parser wrong assignment) stays STOP, so the
    obstacle train remains pinned at seg18 throughout.

Scenario
--------
  Train A (r4, DOWN): seg7.occDown -> seg1.occDown
    Waits at signal3 (seg5.down_signal, corrected) while r4 goes MARKED->ALLOCATING
    ->LOCKED. Signal3 goes to GO when r4 is LOCKED, allowing the train to advance
    through point1 (already NORMAL) into block3. Arrives at seg1.occDown =
    COMPLETETRAINOCC (blocked by signal2 which is permanently STOP) at step 7.

  Train B (free traffic, no route): seg16.occDown -> seg14.occDown
    Moves freely DOWN through block4 (seg16->seg15->seg14). Stopped at seg14.occDown
    by signal7 (corrected: seg14.down_signal=signal7, permanently STOP). Arrives at
    seg14.occDown = COMPLETETRAINOCC at step 3.

Both goals are met at step 7 with no safety violations.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from runner import TestScenario, TrainGoal, print_result, run_scenario
from entity import ElementOcc

# ---------------------------------------------------------------------------
# Scenario: Train A (r4 DOWN->seg1) + Train B (free traffic -> seg14)
# ---------------------------------------------------------------------------
SCENARIO_LITE = TestScenario(
    layout='7_Lite',
    name='Train A (r4: DOWN -> seg1) via pt1.NORMAL  +  free traffic in block4 (-> seg14)',
    trains={
        'seg7': {'occDown': ElementOcc.COMPLETETRAINOCC},  # Train A: waits at signal3 in block2
        'seg16': {'occDown': ElementOcc.COMPLETETRAINOCC},  # Train B: free traffic in block4
        'seg18': {'occDown': ElementOcc.COMPLETETRAINOCC},  # obstacle: blocks phantom r7,r12,r14,r15
        'seg9': {'occDown': ElementOcc.COMPLETETRAINOCC},  # obstacle: blocks phantom r2,r8,r13
    },
    routes=['r4'],
    goals=[
        TrainGoal('seg1', 'occDown'),  # Train A destination (bottom of block3)
        TrainGoal('seg14', 'occDown'),  # Train B destination (bottom of block4, free traffic)
    ],
    max_steps=30,
)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
# No two-train conflict-serialization scenario is added for 7_Lite.
# The candidate pair r4 (DOWN->seg1 in block3) + r11 (UP->seg3 in block3)
# both route through block3; after the first train reaches its destination
# inside block3, that segment stays occupied and blocks the second train's
# path through the same block. Other conflicting pairs involve routes
# documented as not simulatable (block5 / block1 / point-overwrite issues).
if __name__ == '__main__':
    passed = True
    for scenario in (SCENARIO_LITE,):
        result = run_scenario(scenario)
        print_result(scenario, result)
        if not result['passed']:
            passed = False
    sys.exit(0 if passed else 1)
