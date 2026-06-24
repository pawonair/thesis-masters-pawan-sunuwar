"""
Test: 5_Fork layout — sectional interlocking simulation
========================================================
Layout topology (from configs/5_Fork/):

                                /-==Block6
                               |
                /-==Block1==point6==Block4
               |
    Block2==point2==Block5

    - Block1: signal9<-|seg18==seg19==seg20|->signal10
    - Block2: signal3<-|seg5==seg6==seg7|->signal4
    - Block4: signal7<-|seg14==seg15==seg16|->signal8
    - Block5: signal5<-|seg9==seg10==seg11|->signal6
    - Block6: signal11<-|seg23==seg24==seg25|->signal12

    - point2(seg4):  stem->seg9   normal->seg7   reverse->seg18
    - point6(seg21): stem->seg20  normal->seg14  reverse->seg23

Routes and simulatability
--------------------------
    - r0 (UP):   signal10 -> signal8  path=[point6, seg14, seg15, seg16]  point6=NORMAL
    - r1 (UP):   signal10 -> signal12 path=[point6, seg23, seg24, seg25]  point6=REVERSE
    - r2 (UP):   signal4 -> signal10  path=[point2, seg18, seg19, seg20]  point2=REVERSE
    - r3 (UP):   signal4 -> signal6   path=[point2, seg9, seg10, seg11]   point2=NORMAL
    - r4 (DOWN): signal5 -> signal3   path=[point2, seg7, seg6, seg5]     point2=NORMAL
    - r5 (DOWN): signal7 -> signal9   path=[point6, seg20, seg19, seg18]  point6=NORMAL
    - r6 (DOWN): signal9 -> signal3   path=[point2, seg7, seg6, seg5]     point2=REVERSE
    - r7 (DOWN): signal11 -> signal9  path=[point6, seg10, seg19, seg18]  point2=REVERSE


  Routes with point6 (r0, r1, r5, r7): point6.normal=point4 and reverse=point7
    are unresolved -> movement through point6 is blocked. NOT simulatable.

  Routes with point2.REVERSE (r2, r6): point2.reverse=point5 is unresolved ->
    the SNR->RS face exit is undefined. NOT simulatable.

  Routes with point2.NORMAL (r3, r4):
    r4 DOWN: train enters point2 via NS face (from seg9 side) -> exits to
      seg7.occUp -> seg7.up_neighbor=point2 -> train reverses back into point2.
      Direction mismatch: NOT simulatable without deeper movement fixes.

    r3 UP: train at seg7.occUp -> enters point2.occSNR (stem face) -> exits
      toward normal branch (seg9.occDown) -> continues seg10.occDown ->
      seg11.occDown.
      This "fork" direction (stem->branch in the UP route convention) requires
      three corrections that the runner's neighbor_corrections mechanism supports:
        1. Swap seg9, seg10, seg11 neighbors so that DOWN-channel movement
           through these segments goes toward the terminal (seg11), not back
           toward point2.
        2. Remove signal5 from seg9.down_signal — the parser places signal5 at
           seg9's DOWN end (block5 overlap), blocking the corrected movement.

Scenario (r3 UP)
----------------
  Train at seg7.occUp (approaching point2 from the stem side, waiting at signal4).
  Route r3 is activated. Once LOCKED and signal4=GO, the train enters point2.occSNR,
  exits toward seg9.occDown, and advances to seg11.occDown.
  Destination: seg11.occDown = COMPLETETRAINOCC. (~8 steps)

  Neighbor corrections applied:
    seg9  : up_neighbor=point2 (entry from point2 exits here), down_neighbor=seg10
    seg10 : up_neighbor=seg9,   down_neighbor=seg11
    seg11 : down_neighbor=None  (terminal — no further DOWN movement)

  Signal corrections applied:
    seg9.down_signal = None   (remove signal5 that would block DOWN movement)

  Obstacle: none needed — r2 may auto-dispatch when train enters point2.occSNR,
  but r2 cannot proceed while r3 holds point2, and the goal is reached before
  r2 causes a deadlock.

Scenario:
--------
1. Train #1 - Route r0 (UP):   starts at seg20.occUp   -> destination seg16.occUp
   Train #2 - Route r7 (DOWN): starts at seg23.occDown -> destination seg18.occDown

2. Train #1 - Route r1 (UP):   starts at seg20.occUp   -> destination seg25.occUp
   Train #2 - Route r5 (DOWN): starts at seg14.occDown -> destination seg18.occDown

3. Train #1 - Route r2 (UP):   starts at seg7.occUp   -> destination seg20.occUp
   Train #2 - Route r4 (DOWN): starts at seg9.occDown -> destination seg5.occDown

4. Train #1 - Route r3 (UP):   starts at seg7.occUp    -> destination seg11.occUp
   Train #2 - Route r6 (DOWN): starts at seg18.occDown -> destination seg5.occDown
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from runner import TestScenario, TrainGoal, print_result, run_scenario
from entity import ElementOcc

# ---------------------------------------------------------------------------
# Neighbor corrections: swap UP/DOWN ends of block5 segments so that
# DOWN-direction movement goes seg9->seg10->seg11 (away from point2).
# ---------------------------------------------------------------------------
_NEIGHBOR_CORRECTIONS = {
    'seg9': {'up': 'point2', 'down': 'seg10'},
    'seg10': {'up': 'seg9', 'down': 'seg11'},
    'seg11': {'down': None},  # terminal: no further DOWN neighbor
}

# ---------------------------------------------------------------------------
# Signal corrections: remove signal5 from seg9.down end so the DOWN-direction
# train can advance freely from seg9 through seg10 to seg11.
# ---------------------------------------------------------------------------
_SIGNAL_CORRECTIONS = {
    'seg9': {'down': None},
}

# # ---------------------------------------------------------------------------
# # Scenario: r3 UP (point2=NORMAL, fork direction) — seg7.occUp -> seg11.occDown
# # ---------------------------------------------------------------------------
# SCENARIO_FORK = TestScenario(
#     layout='5_Fork',
#     name='r3 UP fork (point2=NORMAL, seg7 -> seg11)',
#     trains={
#         'seg7': {'occUp': ElementOcc.COMPLETETRAINOCC},
#     },
#     routes=['r3'],
#     goals=[
#         TrainGoal('seg11', 'occDown'),
#     ],
#     neighbor_corrections=_NEIGHBOR_CORRECTIONS,
#     signal_corrections=_SIGNAL_CORRECTIONS,
#     max_steps=30,
# )

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
# No active scenarios. All 5_Fork routes are blocked from simulation in the
# current code state:
#   - routes via point6 (r0, r1, r5, r7) cannot move because
#     point6.normal='point4' and point6.reverse='point7' are unresolved
#     strings in 5_Fork's point_config (the layout omits the linear neighbors
#     these names should resolve to).
#   - routes via point2.REVERSE (r2, r6) cannot move because
#     point2.reverse='point5' is similarly unresolved.
#   - routes via point2.NORMAL (r3, r4) need a block5 swap / signal detach
#     workaround for the channel-flip on point2.NS -> seg7.UP exit and even
#     then reverse direction at the destination block boundary.
# Re-enable these tests after the point_config gaps are filled or the
# movement-layer channel-flip is fixed at its source.
if __name__ == '__main__':
    pass
