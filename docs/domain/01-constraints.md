# Hard Constraints — model form

Restatement of Ground Reality Report §23 in the variable names used by
`packages/optimizer`. Every constraint in code cites its `HC-xxx` id in a comment.
All are marked VERIFIED in the source report; none may be relaxed to help the UI.

Variables: `s[i]`,`e[i]` start/end of task *i*; `p[i]` presence literal; `bs[b]`,`be[b]`
block *b* start/end; `pos[i]` metres along section; `H` = clear headway (min).

| ID | Rule | Model form | Phase |
|---|---|---|---|
| HC-001 | Passenger path disjunction (GR 4.08/15.06) | for train *j* on same (section,track): `s[i] >= exit_j + H` OR `entry_j >= e[i] + H` via reified literal | 6a |
| HC-002 | Minimum machine block duration (IRTMM ch.3) | `e[i] - s[i] >= MIN_DURATION[machine]` (BCM 240, CSM 150, UNIMAT 150, TRT 240, DGS 120, TW 120) | 6a |
| HC-003 | OHE isolation before work (ACTM 20603) | `s[i] >= ptw_grant + 20` | 6a |
| HC-004 | Energization buffer (ACTM 20610) | `power_block_end >= e[i] + 15` | 6b |
| HC-005 | S&T disconnection T/351 (SEM 11.4) | `s[i] >= t351_endorsed` | 6a |
| HC-006 | Correspondence testing (Board post-2023) | `block_clear >= e[i] + 30` for point/detection work | 6b |
| HC-007 | Turnout renewal sequence (JPO) | SNT disconnect → TRD isolate → ENGG replace → TRD align → SNT reconnect, chained `s >= e` | 6a |
| HC-008 | Machine spacing 200 m (IRTMM 3.2.1) | `abs(pos[m2] - pos[m1]) >= 200` when intervals overlap | 6b |
| HC-009 | Single machine occupancy | `AddNoOverlap(intervals of machine m)` | 6b |
| HC-010 | Adjacent line infringement (IRPWM 806) | emitted as Caution Order T/409 consequence, speed ≤ 45 | 6b (consequence) |
| HC-011 | IMR flaw within 72 h (USFD 6.3) | `s[i] <= detected_at + 4320` and task forced present | 6b |
| HC-012 | Tower wagon blocks the track (ACTM VI) | same adjacent-track disjunction as HC-010, plus machine transit between sections (sequence-dependent setup) | enforced |
| HC-013 | Gang transit feasibility | `s[B] >= e[A] + transit[locA][locB]` for same gang | 6b |
| HC-014 | Line-clear occupancy (GR XIV) | `bs[b] >= train_exit` | 6b |
| HC-015 | Daylight for non-illuminated work | `s[i] >= sunrise, e[i] <= sunset` unless `has_mobile_lighting` | 6b |
| HC-016 | Max 4 h continuous weekday block | `be[b] - bs[b] <= 240` unless MEGA/Sunday | 6b |
| HC-017 | Track circuit continuity (SEM 11.12) | tamping/renewal requires an SNT escort resource over its interval | 6b |
| HC-018 | Post-block temporary SR (IRPWM 308) | emitted as SR footprint: 20/45/75 kmph over days 1–3 | 6b (consequence) |

**Consequences are constraints too.** HC-010, HC-012 and HC-018 do not forbid a block,
they change what happens after it. Three mechanisms carry them:

1. **Disjunction** -- no maintenance on the parallel track while infringing machine
   work or a tower wagon occupies this one; a machine cannot appear in two sections
   without the transit time to get there.
2. **Budget** -- `config/objectives.yaml: speed_restriction.max_concurrent_km` caps
   how much of the corridor may sit under the severe (20 kmph) restriction at once.
   Days 2 and 3 at 45 / 75 kmph are priced, not rationed.
3. **Recompute** -- `optimizer/traingraph.py` applies the caution orders and speed
   restrictions to the working timetable, cascading each train's lost time down its
   own path, and `solve()` re-solves against that graph until the schedule stops
   colliding with the timetable it creates. The audit re-checks HC-001 against the
   recomputed graph: a plan that only works if its own consequences are ignored is
   rejected.

Delay is always computed over the **restricted length**, never the whole section. A
300 m turnout renewal does not put 36 km at 20 kmph, and pricing it as if it did makes
the optimizer refuse work it should be doing.

## Compatibility (§9.1) — not a distance test

| Pair | Verdict |
|---|---|
| CSM tamping + track-circuit bond check + tower wagon (>200 m) | COMPATIBLE |
| BCM deep screening + point machine maintenance / catenary replacement | STRICTLY_INCOMPATIBLE |
| Turnout renewal (ENGG + SNT + TRD) | SEQUENTIALLY_COMPATIBLE (HC-007 order) |
| Manual rail renewal + GJ replacement + OHE bracket | COMPATIBLE (power block if within 2 m of OHE) |
| Rail de-stressing + axle counter calibration + live OHE | CONDITIONAL |
| Deep screening under live OHE | STRICTLY_PROHIBITED (ACTM 20.3, 2 m clearance) |

Any pair not listed defaults to **INCOMPATIBLE**. Co-location never implies compatibility.
