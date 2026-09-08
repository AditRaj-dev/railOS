"""Block Opportunity Engine.

Finds maintenance opportunities from the working timetable even when no department
has asked for a block. Pure interval arithmetic -- no solver, no heuristics worth
arguing about: a window either has no train path in it or it does.

HC-001 lives here in its simplest form: an opportunity never overlaps a charted
train path, including the clear headway either side. The optimizer re-imposes the
same rule on the tasks themselves, because tasks are not obliged to use an
opportunity we found.
"""

from railos_model import (
    BlockType,
    MaintenanceTask,
    Opportunity,
    ScenarioWorld,
    ScheduledBlock,
    Track,
)

#: Minutes of clearance either side of a charted train path (GR 4.08 / 15.06).
DEFAULT_HEADWAY = 15

#: Below this, a possession is not worth the paperwork.
DEFAULT_MIN_MINUTES = 45

#: Trains within this radius of the window count towards traffic impact.
_IMPACT_RADIUS = 60


def free_intervals(
    world: ScenarioWorld,
    section_id: str,
    track: Track,
    headway: int = DEFAULT_HEADWAY,
) -> list[tuple[int, int]]:
    """Horizon minus every train occupancy on this (section, track)."""
    busy = sorted(
        (max(0, t.entry - headway), min(world.horizonMinutes, t.exit + headway))
        for t in world.trains
        if t.sectionId == section_id and t.track == track
    )
    free: list[tuple[int, int]] = []
    cursor = 0
    for start, end in busy:
        if start > cursor:
            free.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < world.horizonMinutes:
        free.append((cursor, world.horizonMinutes))
    return free


def _traffic_impact(world: ScenarioWorld, section_id: str, start: int, end: int) -> str:
    near = sum(
        1
        for t in world.trains
        if t.sectionId == section_id
        and t.entry < end + _IMPACT_RADIUS
        and t.exit > start - _IMPACT_RADIUS
    )
    if near == 0:
        return "LOW"
    return "MEDIUM" if near <= 2 else "HIGH"


def _candidates(world: ScenarioWorld, section_id: str, track: Track, minutes: int) -> list[str]:
    return [
        t.taskId
        for t in world.tasks
        if t.sectionId == section_id and t.track == track and t.estimatedDuration <= minutes
    ]


def detect(
    world: ScenarioWorld,
    min_minutes: int = DEFAULT_MIN_MINUTES,
    headway: int = DEFAULT_HEADWAY,
) -> list[Opportunity]:
    """Every feasible maintenance window on the corridor, largest first."""
    out: list[Opportunity] = []
    n = 0
    for corridor in world.corridors:
        for section in corridor.sections:
            for track in section.tracks:
                for start, end in free_intervals(world, section.sectionId, track, headway):
                    minutes = end - start
                    if minutes < min_minutes:
                        continue
                    n += 1
                    out.append(
                        Opportunity(
                            opportunityId=f"OP-{n:03d}",
                            sectionId=section.sectionId,
                            track=track,
                            start=start,
                            end=end,
                            minutes=minutes,
                            trafficImpact=_traffic_impact(world, section.sectionId, start, end),
                            candidateTaskIds=_candidates(world, section.sectionId, track, minutes),
                        )
                    )
    return sorted(out, key=lambda o: (-o.minutes, o.start))


def charted(world: ScenarioWorld) -> list[Opportunity]:
    """Opportunities that the WTT already publishes as corridor block windows."""
    return [
        Opportunity(
            opportunityId=w.windowId,
            sectionId=w.sectionId,
            track=w.track,
            start=w.start,
            end=w.end,
            minutes=w.end - w.start,
            trafficImpact=_traffic_impact(world, w.sectionId, w.start, w.end),
            candidateTaskIds=_candidates(world, w.sectionId, w.track, w.end - w.start),
        )
        for w in world.windows
        if w.availability == "AVAILABLE"
    ]


def detect_shadow(
    world: ScenarioWorld,
    primary_blocks: list[ScheduledBlock],
    min_overlap: int = 60,
    headway: int = DEFAULT_HEADWAY,
) -> list[Opportunity]:
    """Shadow blocks (Ground Reality Report 2.3 #4).

    A line does not have to be idle by luck. When a primary block is taken on one
    track, the parallel line is often starved of traffic for the same period --
    that idle time is free maintenance capacity nobody asks for. We report it only
    where the parallel line is genuinely clear of charted paths.
    """
    out: list[Opportunity] = []
    n = 0
    for block in primary_blocks:
        for corridor in world.corridors:
            for section in corridor.sections:
                if section.sectionId != block.sectionId:
                    continue
                for track in section.tracks:
                    if track == block.track:
                        continue
                    for start, end in free_intervals(world, section.sectionId, track, headway):
                        lo, hi = max(start, block.start), min(end, block.end)
                        if hi - lo < min_overlap:
                            continue
                        n += 1
                        out.append(
                            Opportunity(
                                opportunityId=f"SHADOW-{n:03d}",
                                sectionId=section.sectionId,
                                track=track,
                                start=lo,
                                end=hi,
                                minutes=hi - lo,
                                trafficImpact=_traffic_impact(world, section.sectionId, lo, hi),
                                blockType=BlockType.SHADOW,
                                shadowOf=block.blockId,
                                candidateTaskIds=_candidates(
                                    world, section.sectionId, track, hi - lo
                                ),
                            )
                        )
    return out


def fits(task: MaintenanceTask, opportunity: Opportunity) -> bool:
    return (
        task.sectionId == opportunity.sectionId
        and task.track == opportunity.track
        and task.estimatedDuration <= opportunity.minutes
    )
