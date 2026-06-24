# 🚝 SWTbahn Sectional Interlocking: Formal Model and Verification

Formal modeling and NuXmV verification of a **sectional interlocking algorithm** for
the [SWTbahn](https://www.uni-bamberg.de/swt/) digital model railway at Otto-Friedrich-Universität Bamberg.

The project produces NuXmV SMV models in two ways: a hand-crafted model for one specific two-train scenario, and a
Python generator pipeline that auto-generates correct SMV models from declarative YAML layout configurations. Six
generated layouts have been fully verified - 266 safety and liveness properties, 0 failures.

---

## Requirements

- **Python 3.14,4** (uses `StrEnum` from `entity.py`) with **PyYAML** installed
- **NuXmV 2.1.0** (download from [nuxmv.fbk.eu](https://nuxmv.fbk.eu/download.html) and ensure `nuXmv` is on your
  `PATH`)

Install Python dependencies:

```bash
pip install pyyaml
```

---

## Repository Structure

```
app/                             Python SMV generator pipeline
|-- main.py                      CLI entry point
|-- entity.py                    Linear, Point, Route, Signal dataclasses
|-- parser.py                    YAML config reader
|-- generate_sec_next.py         next(occ*) occupancy transition functions
|-- generate_route_next.py       Route state machine (FREE -> MARKED -> … -> OCCUPIED)
|-- generate_lock_trans_next.py  Element mode/prev locking transitions
|-- generate_ltlspecs.py         LTLSPEC liveness properties
|-- generate_invars.py           INVARSPEC safety properties
|-- generate_assigns.py          ASSIGN init blocks and CMD logic

configs/                         Layout topology definitions (YAML)
|-- 1_Straight/                  Straight bidirectional track (2 routes, 0 points)
|-- 2_Point/                     Single point, 2 active trains (4 routes, 1 point)
|-- 3_Cross/                     Cross junction (6 routes, 2 points)
|-- 4_Mini/                      Mini loop (8 routes, 2 points)
|-- 5_Fork/                      Fork junction (8 routes, 2 points)
|-- 6_Twist/                     Twist topology (8 routes, 2 points)
|-- 7_Lite/                      SWTbahn Lite subset (16 routes, 7 points)
|-- Full/                        Full SWTbahn layout (out of verification scope)

smv_model/
|-- gen_model/                   Auto-generated SMV models (one per layout)
|-- swt-point.smv                Hand-crafted model (two-train, one-point scenario)
|-- prototype.smv                Reference model (read-only)

tools/
|-- generate_smv.sh              Shell wrapper for the Python generator
|-- run_verification.sh          Shell wrapper for NuXmV

VERIFICATION_LOG.md              Full NuXmV results for all layouts
THESIS_REPORT_HANDOFF.md         Complete context export for report writing
```

---

## Generating an SMV Model

### Using the shell wrapper (interactive)

```bash
tools/generate_smv.sh <layout>
```

Available layouts: `1_Straight`, `2_Point`, `3_Cross`, `4_Mini`, `5_Fork`, `6_Twist`, `7_Lite`, `Full`

The script prompts for the starting segment IDs of trains in each direction:

```
Enter the starting position of trains in the following travel direction:
    1) UP: segment ID = 3
    2) DOWN: segment ID = 5
```

These seed the initial train positions (`init(segN.occUp) := COMPLETETRAINOCC` and
`init(segN.occDown) := COMPLETETRAINOCC`). Correct seeding is required for liveness properties to be non-vacuous.

### Using the Python generator directly

```bash
python3 app/main.py -c 2_Point --out smv_model/gen_model/2_Point.smv \
    --seg-up 3 --seg-down 5
```

Options:

- `-c / --config-dir` - layout name (required)
- `--out` - output file path (defaults to stdout)
- `--seg-up N` - segment whose `occUp` is initialised to `COMPLETETRAINOCC`
- `--seg-down N` - segment whose `occDown` is initialised to `COMPLETETRAINOCC`

---

## Running Verification

### Shell wrapper

```bash
tools/run_verification.sh <layout>          # batch mode
tools/run_verification.sh <layout> -int     # interactive mode
```

### Recommended interactive workflow (BDD)

```bash
nuXmv -int smv_model/gen_model/2_Point.smv
```

```
go
dynamic_var_ordering -f sift
print_fair_states
check_invar
check_ltlspec
quit
```

`print_fair_states` must return a non-zero count before checking properties. A zero result means the initial state or
invariants are inconsistent.

To check a single named property:

```
check_invar -P iSys.track.NoHeadToHeadSegmentCollisions
check_ltlspec -P iSys.track.r0TrainReachesSeg7UpEventuallyForever
```

### For large layouts (7_Lite): IC3 and BMC

BDD-based `go` + `check_invar` does not complete in reasonable time for 7_Lite (7 points, 16 routes). Use:

```bash
nuXmv -int smv_model/gen_model/7_Lite.smv
```

```
go_bmc
check_invar_ic3
check_ltlspec_bmc -k 30
quit
```

---

## Verification Results

All models were generated with the corrected generator (6 bugs fixed) and verified with NuXmV 2.1.0.

| Layout     | Lines  | Routes | Fair States | Safety (INVAR)   | Liveness (LTL)     | Total       |
|------------|--------|--------|-------------|------------------|--------------------|-------------|
| 1_Straight | 1,210  | 2      | 29          | 6/6 TRUE         | 6/6 TRUE           | 12/12       |
| 2_Point    | 2,311  | 4      | 77          | 11/11 TRUE       | 22/22 TRUE         | 33/33       |
| 3_Cross    | 3,370  | 6      | 6           | 11/11 TRUE       | 37/37 TRUE         | 48/48       |
| 4_Mini     | 3,742  | 8      | 39          | 11/11 TRUE       | 46/46 TRUE         | 57/57       |
| 5_Fork     | 3,927  | 8      | 6           | 11/11 TRUE       | 46/46 TRUE         | 57/57       |
| 6_Twist    | 4,050  | 8      | 6           | 11/11 TRUE       | 48/48 TRUE         | 59/59       |
| **Total**  |        |        |             | **61/61**        | **205/205**        | **266/266** |
| 7_Lite     | 7,104  | 16     | -           | 11/11 TRUE (IC3) | 0 counterexamples (BMC k=30) | -           |
| Full       | 59,903 | 75     | -           | N/A              | N/A                | -           |

**266 properties verified, 0 failures** across layouts `1_Straight` through `6_Twist`.`

---

## Layout Configuration Files

Each layout directory under `configs/` contains three files:

**`interlocking_table.yml`** - route definitions:

```yaml
interlocking-table:
  - id: 0
    source: signal2
    destination: signal4
    orientation: anticlockwise
    path:
      - id: seg4
      - id: seg5
    points:
      - id: point1
        position: normal
    conflicts:
      - id: 1
      - id: 2
```

**`extras_config.yml`** - block and segment layout (signals, lengths, directions):

```yaml
blocks:
  - id: block2
    main:
      - seg6
    overlaps:
      - seg5    # down boundary
      - seg7    # up boundary
    direction: bidirectional
    signals:
      - signal3  # entry (up direction)
      - signal4  # exit (down direction)
```

**`point_config.yml`** - point neighbour topology:

```yaml
points:
  - id: point1
    seg: 4
    stem: seg5
    normal: seg3
    reverse: seg16
```

---

## Key Concepts

**Sectional release:** Track elements (segments, points) are released behind the advancing train one by one rather than
holding the entire route locked. Each element transitions `EXLOCKED -> USED -> AVAILABLE` as the train passes through
it.

**Occupancy states:** `FREE | HEADOCC | COMPLETETRAINOCC | TAILOCC | ERROROCC`. The `ERROROCC` state represents a
physically impossible occupancy (collision or derailment) and is asserted never to occur.

**Determinism rule:** When the predecessor segment holds `COMPLETETRAINOCC`, the train head *must* enter the current
segment - the result is deterministically `HEADOCC`. Using a non-deterministic set `{HEADOCC, FREE}` here creates an
infinite stuttering path where the train never moves, making all liveness properties unprovable.

**Point occupancy (3-variable scheme):** Points use `occSNR` (stem->branch), `occNS` (normal branch->stem), and
`occRS` (reverse branch->stem) instead of two simple direction variables. This allows direct expression of three-way
head-to-head collision properties and derailment conditions.

**`can_lock` conflict exclusion:** NuXmV uses synchronous semantics - all transitions fire simultaneously. A point
switch takes two steps (e.g., `NORMAL -> INTERMEDIATE -> REVERSE`). Without explicit conflict exclusion in the
`ALLOCATING -> LOCKED` guard, two conflicting routes can both see the old point aspect in the first step, and both lock
simultaneously. The generator adds conflict exclusion to `can_lock` to prevent this race.

---

## Further Reading

- `app/README.md` - sectional release procedure and entity definitions
- `web/README.md` - In-browser static React-based interface with standalone Babel for sectional interlocking system simulation.
