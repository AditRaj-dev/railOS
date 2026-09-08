"""Train-graph consequences of a plan: caution orders and speed restrictions.

HC-010, HC-012 and HC-018 do not stop a block being taken -- they change how trains
run afterwards. A plan that ignores them looks free and is not: a deep screening
buys 24 hours at 20 kmph on that section, and every train pays for it.

This module turns those obligations into numbers, and recomputes the working
timetable under them so the *next* planning pass sees the timetable the plan
actually created. `solve_converged` in `model.py` iterates the two until the answer
stops moving.
"""

from dataclasses import dataclass

from railos_model import Plan, ScenarioWorld, Track, TrainClass

from .config import (
    CAUTION_ORDER_SPEED_KMPH,
    SR_DAY_SPEEDS_KMPH,
)


@dataclass(frozen=True)
class CautionOrder:
    """Form T/409. Imposed on the line adjacent to infringing machine work."""

    sectionId: str
    track: Track
    start: int
    end: int
    speedKmph: int
    cause: str
    lengthKm: float = 1.0

    def describe(self) -> str:
        return (
            f"T/409 caution order: {self.sectionId} {self.track.value} "
            f"[{self.start},{self.end}] at {self.speedKmph} kmph over {self.lengthKm:.1f} km, "
            f"caused by {self.cause}"
        )


@dataclass(frozen=True)
class SpeedRestriction:
    """HC-018. Post-block temporary SR: 20 / 45 / 75 kmph on days 1-3."""

    sectionId: str
    track: Track
    start: int
    cause: str
    lengthKm: float = 1.0

    @property
    def end(self) -> int:
        return self.start + len(SR_DAY_SPEEDS_KMPH) * 1440

    def speed_at(self, minute: int) -> int | None:
        if not self.start <= minute < self.end:
            return None
        return SR_DAY_SPEEDS_KMPH[(minute - self.start) // 1440]

    def describe(self) -> str:
        speeds = " / ".join(str(s) for s in SR_DAY_SPEEDS_KMPH)
        return (
            f"Temporary SR: {self.sectionId} {self.track.value} from minute {self.start} "
            f"for {len(SR_DAY_SPEEDS_KMPH)} days at {speeds} kmph, caused by {self.cause}"
        )


def _section(world: ScenarioWorld, section_id: str):
    for corridor in world.corridors:
        for section in corridor.sections:
            if section.sectionId == section_id:
                return section
    return None


def _other_track(track: Track) -> Track:
    return Track.DOWN if track is Track.UP else Track.UP


MIN_RESTRICTED_KM = 0.1
"""A restriction is never shorter than the approach and clearance either side of the
work site, however short the work itself is."""


def delay_minutes(
    world: ScenarioWorld,
    section_id: str,
    restricted_kmph: int,
    length_km: float | None = None,
) -> int:
    """Extra running time over the RESTRICTED LENGTH at a restricted speed.

    Delta = dist/restricted - dist/mps, in minutes, rounded up: railway timings are
    kept in whole minutes and a controller never plans a fractional path.

    `length_km` is the length actually under restriction -- a 300 m turnout renewal
    does not put 36 km of section at 20 kmph, and pricing it as if it did makes the
    optimizer refuse work it should be doing. Defaults to the whole section only when
    no worked length is known.
    """
    section = _section(world, section_id)
    if section is None or restricted_kmph <= 0:
        return 0
    km = section.lengthKm if length_km is None else max(length_km, MIN_RESTRICTED_KM)
    delta = (km / restricted_kmph - km / section.mps) * 60.0
    return max(0, int(delta + 0.999))


def worked_km(task) -> float:
    return max(abs(task.kmEnd - task.kmStart), MIN_RESTRICTED_KM)


def caution_orders(world: ScenarioWorld, plan: Plan) -> list[CautionOrder]:
    """HC-010 and HC-012: machine work that infringes the adjacent line, and tower
    wagons whose booms and wire spans reach across it, impose a caution order on the
    parallel track for the whole possession."""
    out: list[CautionOrder] = []
    blocks = {b.blockId: b for b in plan.blocks}
    for a in plan.assignments:
        task = world.task(a.taskId)
        wagon = task.machineType.value == "TOWER_WAGON"
        if not (task.infringesAdjacent or wagon):
            continue
        block = blocks[a.blockId]
        out.append(
            CautionOrder(
                sectionId=task.sectionId,
                track=_other_track(task.track),
                start=block.start,
                end=block.end,
                speedKmph=CAUTION_ORDER_SPEED_KMPH,
                cause=f"{task.taskId} ({'tower wagon, HC-012' if wagon else 'HC-010'})",
                lengthKm=worked_km(task),
            )
        )
    return out


def speed_restrictions(world: ScenarioWorld, plan: Plan) -> list[SpeedRestriction]:
    """HC-018: what the plan leaves behind on the track it just worked."""
    return [
        SpeedRestriction(
            sectionId=world.task(a.taskId).sectionId,
            track=world.task(a.taskId).track,
            start=a.end,
            cause=a.taskId,
            lengthKm=worked_km(world.task(a.taskId)),
        )
        for a in plan.assignments
        if world.task(a.taskId).imposesSpeedRestriction
    ]


def recompute(world: ScenarioWorld, plan: Plan) -> ScenarioWorld:
    """Return the timetable as it will actually run under this plan.

    A train crossing a restricted section loses time there and carries that loss
    into every later section of its own run -- late is late, it does not evaporate
    at the section boundary.
    """
    out = world.model_copy(deep=True)
    orders = caution_orders(world, plan)
    restrictions = speed_restrictions(world, plan)

    # Process each train's movements in order so delay cascades down its path.
    by_train: dict[str, list] = {}
    for mv in out.trains:
        by_train.setdefault(mv.trainId, []).append(mv)

    for movements in by_train.values():
        movements.sort(key=lambda m: m.entry)
        carried = 0
        for mv in movements:
            mv.entry += carried
            mv.exit += carried
            extra = 0
            for order in orders:
                if (
                    order.sectionId == mv.sectionId
                    and order.track == mv.track
                    and mv.entry < order.end
                    and order.start < mv.exit
                ):
                    extra = max(
                        extra,
                        delay_minutes(out, mv.sectionId, order.speedKmph, order.lengthKm),
                    )
            for sr in restrictions:
                if sr.sectionId != mv.sectionId or sr.track != mv.track:
                    continue
                speed = sr.speed_at(mv.entry)
                if speed:
                    extra = max(
                        extra, delay_minutes(out, mv.sectionId, speed, sr.lengthKm)
                    )
            mv.exit += extra
            mv.delayMinutes += carried + extra
            carried += extra
    return out


def disruption(world: ScenarioWorld, plan: Plan, class_weights: dict[str, int]) -> dict:
    """Weighted delay the plan actually causes, by class and in total."""
    after = recompute(world, plan)
    before = {(m.trainId, m.sectionId, m.track): m for m in world.trains}
    total = 0
    weighted = 0.0
    by_class: dict[str, int] = {}
    for mv in after.trains:
        original = before.get((mv.trainId, mv.sectionId, mv.track))
        if original is None:
            continue
        lost = (mv.exit - mv.entry) - (original.exit - original.entry)
        if lost <= 0:
            continue
        total += lost
        weighted += lost * class_weights.get(mv.trainClass.value, 10) / 10.0
        by_class[mv.trainClass.value] = by_class.get(mv.trainClass.value, 0) + lost
    return {
        "trainDisruptionMinutes": total,
        "weightedDisruption": round(weighted, 2),
        "byClass": by_class,
        "premiumMinutes": sum(
            v
            for k, v in by_class.items()
            if k in (TrainClass.RAJDHANI.value, TrainClass.VANDE_BHARAT.value)
        ),
    }
