"""Synthetic dataset generator for the GZB-ALJN corridor.

Produces the nine files of Ground Reality Report section 15. Deterministic: the same
inputs always produce the same JSON, so plan metrics are reproducible.

SYNTHETIC DATA. This is not a TMS / SMMS / TDMS / COA / BDMS extract and must never
be presented as one. Structure and vocabulary follow the verified field registers;
values are invented for demonstration.

    python -m railos_data.generate datasets
"""

import json
import pathlib
import sys

from railos_model import (
    Asset,
    BlockSection,
    BlockType,
    BlockWindow,
    Corridor,
    Defect,
    Department,
    Dependency,
    GoodsForecast,
    LineConfig,
    MachineType,
    MaintenanceTask,
    Resource,
    Severity,
    TaskType,
    Track,
    TrainClass,
    TrainMovement,
)

HORIZON_MINUTES = 4320  # 72 h
HORIZON_START_ISO = "2026-09-09T00:00:00+05:30"
DAY = 1440

# --- corridor -------------------------------------------------------------
# Delhi-Howrah main line, Ghaziabad - Aligarh Jn. Four block sections, double line.
SECTIONS = [
    # sectionId, from, to, start_m, end_m, run_minutes, mps_kmph
    ("SEC_GZB_DER", "GZB", "DER", 0, 24_000, 22, 110),
    ("SEC_DER_KRJ", "DER", "KRJ", 24_000, 52_000, 25, 130),
    ("SEC_KRJ_SMQ", "KRJ", "SMQ", 52_000, 88_000, 28, 130),
    ("SEC_SMQ_ALJN", "SMQ", "ALJN", 88_000, 126_000, 30, 110),
]


def _corridor() -> Corridor:
    return Corridor(
        corridorId="GZB-ALJN",
        name="Ghaziabad - Aligarh Junction",
        lineConfig=LineConfig.DOUBLE,
        tracks=[Track.UP, Track.DOWN],
        sections=[
            BlockSection(
                sectionId=sid,
                fromStation=a,
                toStation=b,
                startM=s,
                endM=e,
                tracks=[Track.UP, Track.DOWN],
                mps=mps,
            )
            for sid, a, b, s, e, _run, mps in SECTIONS
        ],
    )


# --- assets ---------------------------------------------------------------
def _assets() -> list[Asset]:
    out: list[Asset] = []
    for sid, a, b, start, end, _run, _mps in SECTIONS:
        for track in (Track.UP, Track.DOWN):
            out.append(
                Asset(
                    assetId=f"TRACK_SEC_{a}_{b}_{track.value}",
                    assetType="TRACK_SECTION",
                    sectionId=sid,
                    track=track,
                    locationM=start,
                    criticality=9 if track is Track.UP else 8,
                    oheElementarySection=f"OHE_ELEM_{2040 + SECTIONS.index((sid, a, b, start, end, _run, _mps))}_{b}",
                )
            )
        out.append(
            Asset(
                assetId=f"OHE_ELEM_{2040 + SECTIONS.index((sid, a, b, start, end, _run, _mps))}_{b}",
                assetType="OHE_ELEMENTARY_SECTION",
                sectionId=sid,
                locationM=(start + end) // 2,
                criticality=8,
            )
        )
    # Interlocked points at the junction stations.
    out += [
        Asset(
            assetId="POINT_102B_KRJ",
            assetType="POINT",
            sectionId="SEC_KRJ_SMQ",
            track=Track.UP,
            locationM=52_100,
            criticality=10,
            oheElementarySection="OHE_ELEM_2042_SMQ",
        ),
        Asset(
            assetId="POINT_14A_DER",
            assetType="POINT",
            sectionId="SEC_DER_KRJ",
            track=Track.DOWN,
            locationM=24_300,
            criticality=9,
            oheElementarySection="OHE_ELEM_2041_KRJ",
        ),
        Asset(
            assetId="AXLE_COUNTER_DER_KRJ_UP",
            assetType="AXLE_COUNTER",
            sectionId="SEC_DER_KRJ",
            track=Track.UP,
            locationM=38_000,
            criticality=7,
        ),
    ]
    return out


# --- working timetable ----------------------------------------------------
# (trainId, class, priority, departure minute from GZB on day 0, direction)
UP_TRAINS = [
    ("12002", TrainClass.VANDE_BHARAT, 10, 6 * 60 + 15),
    ("12310", TrainClass.RAJDHANI, 10, 17 * 60 + 20),
    ("12417", TrainClass.MAIL_EXPRESS, 8, 22 * 60 + 30),
    ("12312", TrainClass.MAIL_EXPRESS, 8, 4 * 60 + 20),
    ("14207", TrainClass.PASSENGER, 5, 9 * 60 + 40),
    ("64556", TrainClass.SUBURBAN, 7, 8 * 60 + 10),
    ("64562", TrainClass.SUBURBAN, 7, 18 * 60 + 40),
]
DOWN_TRAINS = [
    ("12001", TrainClass.VANDE_BHARAT, 10, 7 * 60 + 5),
    ("12309", TrainClass.RAJDHANI, 10, 16 * 60 + 45),
    ("12418", TrainClass.MAIL_EXPRESS, 8, 21 * 60 + 10),
    ("12311", TrainClass.MAIL_EXPRESS, 8, 5 * 60 + 30),
    ("14208", TrainClass.PASSENGER, 5, 11 * 60 + 25),
    ("64555", TrainClass.SUBURBAN, 7, 9 * 60 + 15),
]


def _train_movements() -> list[TrainMovement]:
    """Three days of the WTT. The 01:10-04:00 band is deliberately traffic-free -
    that is where corridor maintenance blocks actually live on this route."""
    out: list[TrainMovement] = []
    for day in range(HORIZON_MINUTES // DAY):
        for track, roster, order in (
            (Track.UP, UP_TRAINS, SECTIONS),
            (Track.DOWN, DOWN_TRAINS, list(reversed(SECTIONS))),
        ):
            for train_id, klass, prio, dep in roster:
                t = day * DAY + dep
                for sid, _a, _b, _s, _e, run, _mps in order:
                    out.append(
                        TrainMovement(
                            trainId=f"{train_id}",
                            sectionId=sid,
                            track=track,
                            entry=t,
                            exit=t + run,
                            trainClass=klass,
                            priority=prio,
                        )
                    )
                    t += run
    return out


def _goods_forecast() -> list[GoodsForecast]:
    """Freight paths are probabilistic on IR - a rake is expected within a window,
    not at a minute. SO-004 prices detention against these."""
    out: list[GoodsForecast] = []
    for day in range(HORIZON_MINUTES // DAY):
        base = day * DAY
        out += [
            GoodsForecast(
                rakeId=f"GDS-{day}-01",
                sectionId="SEC_DER_KRJ",
                track=Track.DOWN,
                windowStart=base + 60,
                windowEnd=base + 240,
                probability=0.8,
                priorityWeight=1.2,
            ),
            GoodsForecast(
                rakeId=f"GDS-{day}-02",
                sectionId="SEC_KRJ_SMQ",
                track=Track.UP,
                windowStart=base + 150,
                windowEnd=base + 330,
                probability=0.6,
                priorityWeight=1.0,
            ),
            GoodsForecast(
                rakeId=f"GDS-{day}-03",
                sectionId="SEC_SMQ_ALJN",
                track=Track.DOWN,
                windowStart=base + 13 * 60,
                windowEnd=base + 16 * 60,
                probability=0.7,
                priorityWeight=1.5,
            ),
        ]
    return out


def _block_windows() -> list[BlockWindow]:
    """Corridor blocks charted in the WTT itself."""
    out: list[BlockWindow] = []
    for day in range(HORIZON_MINUTES // DAY):
        base = day * DAY
        for i, (sid, *_rest) in enumerate(SECTIONS):
            out.append(
                BlockWindow(
                    windowId=f"WIN-{day}{i}1",
                    sectionId=sid,
                    track=Track.UP,
                    start=base + 70,
                    end=base + 235,
                )
            )
            out.append(
                BlockWindow(
                    windowId=f"WIN-{day}{i}2",
                    sectionId=sid,
                    track=Track.DOWN,
                    start=base + 90,
                    end=base + 255,
                )
            )
    return out


# --- resources ------------------------------------------------------------
def _resources() -> list[Resource]:
    return [
        Resource(resourceId="CSM-104", resourceType="MACHINE", machineType=MachineType.CSM,
                 department=Department.ENGG, homeDepot="GZB Machine Depot", homeSectionId="SEC_GZB_DER"),
        Resource(resourceId="BCM-71", resourceType="MACHINE", machineType=MachineType.BCM,
                 department=Department.ENGG, homeDepot="TDL Machine Depot", homeSectionId="SEC_DER_KRJ"),
        Resource(resourceId="UNIMAT-22", resourceType="MACHINE", machineType=MachineType.UNIMAT,
                 department=Department.ENGG, homeDepot="GZB Machine Depot", homeSectionId="SEC_KRJ_SMQ"),
        Resource(resourceId="TW-4501", resourceType="MACHINE", machineType=MachineType.TOWER_WAGON,
                 department=Department.TRD, homeDepot="GZB TRD Depot", homeSectionId="SEC_GZB_DER"),
        Resource(resourceId="ENGG-GANG-GZB", resourceType="GANG", department=Department.ENGG,
                 homeDepot="GZB PWI", homeSectionId="SEC_GZB_DER"),
        Resource(resourceId="ENGG-GANG-KRJ", resourceType="GANG", department=Department.ENGG,
                 homeDepot="KRJ PWI", homeSectionId="SEC_KRJ_SMQ"),
        Resource(resourceId="SNT-GANG-KRJ", resourceType="GANG", department=Department.SNT,
                 homeDepot="KRJ SSE(Sig)", homeSectionId="SEC_KRJ_SMQ"),
        Resource(resourceId="SNT-ESCORT-1", resourceType="ESCORT", department=Department.SNT,
                 homeDepot="KRJ SSE(Sig)", homeSectionId="SEC_DER_KRJ"),
        Resource(resourceId="TRD-GANG-DER", resourceType="GANG", department=Department.TRD,
                 homeDepot="DER TRD", homeSectionId="SEC_DER_KRJ"),
    ]


# --- maintenance tasks ----------------------------------------------------
def _tasks() -> list[MaintenanceTask]:
    def t(**kw) -> MaintenanceTask:
        kw.setdefault("corridorId", "GZB-ALJN")
        return MaintenanceTask(**kw)

    return [
        # --- ENGG -------------------------------------------------------
        t(taskId="ENG-1001", department=Department.ENGG, assetId="TRACK_SEC_GZB_DER_UP",
          sectionId="SEC_GZB_DER", track=Track.UP, kmStart=8.2, kmEnd=12.4,
          taskType=TaskType.TAMPING, severity=6, criticality=9, dueMinute=2 * DAY,
          estimatedDuration=180, durationStdDev=25, machineType=MachineType.CSM,
          resourceIds=["CSM-104"], gangId="ENGG-GANG-GZB", requiresSntEscort=True,
          imposesSpeedRestriction=True, overdueDays=12),
        t(taskId="ENG-1002", department=Department.ENGG, assetId="TRACK_SEC_DER_KRJ_DOWN",
          sectionId="SEC_DER_KRJ", track=Track.DOWN, kmStart=31.0, kmEnd=33.5,
          taskType=TaskType.DEEP_SCREENING, severity=7, criticality=8, dueMinute=3 * DAY,
          estimatedDuration=300, durationStdDev=60, machineType=MachineType.BCM,
          resourceIds=["BCM-71"], gangId="ENGG-GANG-KRJ", requiresPTW=True,
          oheElementarySection="OHE_ELEM_2041_KRJ", infringesAdjacent=True,
          imposesSpeedRestriction=True, overdueDays=40),
        t(taskId="ENG-1004", department=Department.ENGG, assetId="POINT_102B_KRJ",
          sectionId="SEC_KRJ_SMQ", track=Track.UP, kmStart=52.1, kmEnd=52.4,
          taskType=TaskType.TURNOUT_RENEWAL, severity=9, criticality=10, dueMinute=2 * DAY,
          estimatedDuration=210, durationStdDev=45, gangId="ENGG-GANG-KRJ",
          requiresPTW=True, requiresT351=True, oheElementarySection="OHE_ELEM_2042_SMQ",
          imposesSpeedRestriction=True, overdueDays=8),
        t(taskId="ENG-1005", department=Department.ENGG, assetId="TRACK_SEC_SMQ_ALJN_UP",
          sectionId="SEC_SMQ_ALJN", track=Track.UP, kmStart=95.0, kmEnd=96.2,
          taskType=TaskType.SLEEPER_RENEWAL, severity=5, criticality=7, dueMinute=3 * DAY,
          estimatedDuration=120, durationStdDev=20, gangId="ENGG-GANG-KRJ",
          hasMobileLighting=False, overdueDays=3),
        t(taskId="ENG-1006", department=Department.ENGG, assetId="TRACK_SEC_DER_KRJ_UP",
          sectionId="SEC_DER_KRJ", track=Track.UP, kmStart=40.0, kmEnd=41.0,
          taskType=TaskType.DESTRESSING, severity=6, criticality=8, dueMinute=3 * DAY,
          estimatedDuration=150, durationStdDev=30, gangId="ENGG-GANG-KRJ", overdueDays=18),
        # --- SNT --------------------------------------------------------
        t(taskId="SNT-2001", department=Department.SNT, assetId="TRACK_SEC_GZB_DER_UP",
          sectionId="SEC_GZB_DER", track=Track.UP, kmStart=9.0, kmEnd=11.8,
          taskType=TaskType.TRACK_CIRCUIT_BOND, severity=4, criticality=7, dueMinute=2 * DAY,
          estimatedDuration=60, durationStdDev=10, gangId="SNT-GANG-KRJ", overdueDays=5),
        t(taskId="SNT-2002", department=Department.SNT, assetId="POINT_14A_DER",
          sectionId="SEC_DER_KRJ", track=Track.DOWN, kmStart=24.3, kmEnd=24.4,
          taskType=TaskType.POINT_MACHINE_MAINT, severity=7, criticality=9, dueMinute=2 * DAY,
          estimatedDuration=90, durationStdDev=15, gangId="SNT-GANG-KRJ",
          requiresT351=True, requiresCorrespondenceTest=True, overdueDays=22),
        t(taskId="SNT-2003", department=Department.SNT, assetId="POINT_102B_KRJ",
          sectionId="SEC_KRJ_SMQ", track=Track.UP, kmStart=52.1, kmEnd=52.2,
          taskType=TaskType.SNT_DISCONNECTION, severity=8, criticality=10, dueMinute=2 * DAY,
          estimatedDuration=45, durationStdDev=10, gangId="SNT-GANG-KRJ", requiresT351=True),
        t(taskId="SNT-2004", department=Department.SNT, assetId="POINT_102B_KRJ",
          sectionId="SEC_KRJ_SMQ", track=Track.UP, kmStart=52.1, kmEnd=52.2,
          taskType=TaskType.SNT_RECONNECTION, severity=8, criticality=10, dueMinute=2 * DAY,
          estimatedDuration=60, durationStdDev=15, gangId="SNT-GANG-KRJ",
          requiresT351=True, requiresCorrespondenceTest=True),
        t(taskId="SNT-2005", department=Department.SNT, assetId="AXLE_COUNTER_DER_KRJ_UP",
          sectionId="SEC_DER_KRJ", track=Track.UP, kmStart=38.0, kmEnd=38.1,
          taskType=TaskType.AXLE_COUNTER_CALIB, severity=5, criticality=7, dueMinute=3 * DAY,
          estimatedDuration=75, durationStdDev=15, gangId="SNT-GANG-KRJ", overdueDays=9),
        # --- TRD --------------------------------------------------------
        t(taskId="TRD-3001", department=Department.TRD, assetId="OHE_ELEM_2040_DER",
          sectionId="SEC_GZB_DER", track=Track.UP, kmStart=8.0, kmEnd=13.0,
          taskType=TaskType.OHE_INSPECTION, severity=4, criticality=7, dueMinute=2 * DAY,
          estimatedDuration=120, durationStdDev=20, machineType=MachineType.TOWER_WAGON,
          resourceIds=["TW-4501"], gangId="TRD-GANG-DER",
          oheElementarySection="OHE_ELEM_2040_DER", overdueDays=6),
        t(taskId="TRD-3002", department=Department.TRD, assetId="OHE_ELEM_2041_KRJ",
          sectionId="SEC_DER_KRJ", track=Track.DOWN, kmStart=31.2, kmEnd=32.0,
          taskType=TaskType.CATENARY_REPLACEMENT, severity=8, criticality=9, dueMinute=3 * DAY,
          estimatedDuration=180, durationStdDev=40, machineType=MachineType.TOWER_WAGON,
          resourceIds=["TW-4501"], gangId="TRD-GANG-DER", requiresPTW=True,
          oheElementarySection="OHE_ELEM_2041_KRJ", overdueDays=15),
        t(taskId="TRD-3003", department=Department.TRD, assetId="OHE_ELEM_2042_SMQ",
          sectionId="SEC_KRJ_SMQ", track=Track.UP, kmStart=52.1, kmEnd=52.4,
          taskType=TaskType.TRD_ISOLATION, severity=8, criticality=10, dueMinute=2 * DAY,
          estimatedDuration=30, durationStdDev=5, gangId="TRD-GANG-DER", requiresPTW=True,
          oheElementarySection="OHE_ELEM_2042_SMQ"),
        t(taskId="TRD-3004", department=Department.TRD, assetId="OHE_ELEM_2042_SMQ",
          sectionId="SEC_KRJ_SMQ", track=Track.UP, kmStart=52.1, kmEnd=52.4,
          taskType=TaskType.OHE_SLEWING, severity=7, criticality=9, dueMinute=2 * DAY,
          estimatedDuration=45, durationStdDev=10, gangId="TRD-GANG-DER", requiresPTW=True,
          oheElementarySection="OHE_ELEM_2042_SMQ"),
        t(taskId="TRD-3005", department=Department.TRD, assetId="TRACK_SEC_SMQ_ALJN_UP",
          sectionId="SEC_SMQ_ALJN", track=Track.UP, kmStart=95.2, kmEnd=96.0,
          taskType=TaskType.OHE_BRACKET_ADJUST, severity=5, criticality=7, dueMinute=3 * DAY,
          estimatedDuration=90, durationStdDev=20, gangId="TRD-GANG-DER", requiresPTW=True,
          oheElementarySection="OHE_ELEM_2043_ALJN", overdueDays=11),
    ]


def _dependencies() -> list[Dependency]:
    """HC-007: turnout renewal is strictly sequenced across three departments."""
    chain = ["SNT-2003", "TRD-3003", "ENG-1004", "TRD-3004", "SNT-2004"]
    return [
        Dependency(
            predecessorTaskId=a,
            successorTaskId=b,
            reason="HC-007 turnout renewal sequence (Joint Procedure Order)",
        )
        for a, b in zip(chain, chain[1:])
    ]


def _defects() -> list[Defect]:
    return [
        Defect(defectId="DEF-9001", assetId="TRACK_SEC_DER_KRJ_DOWN", sectionId="SEC_DER_KRJ",
               severityCode=Severity.OMS_PEAK_HIGH, detectedAtMinute=0, taskId="ENG-1002",
               repeatCount=3),
        Defect(defectId="DEF-9002", assetId="POINT_14A_DER", sectionId="SEC_DER_KRJ",
               severityCode=Severity.POINT_SLACK_DETECTION, detectedAtMinute=0, taskId="SNT-2002",
               repeatCount=2),
        Defect(defectId="DEF-9003", assetId="OHE_ELEM_2041_KRJ", sectionId="SEC_DER_KRJ",
               severityCode=Severity.OHE_DROPPING_FAULT, detectedAtMinute=0, taskId="TRD-3002"),
        Defect(defectId="DEF-9004", assetId="POINT_102B_KRJ", sectionId="SEC_KRJ_SMQ",
               severityCode=Severity.OBS, detectedAtMinute=0, taskId="ENG-1004"),
    ]


FILES = {
    "corridors.json": lambda: [_corridor()],
    "assets.json": _assets,
    "maintenance_tasks.json": _tasks,
    "defects.json": _defects,
    "train_movements.json": _train_movements,
    "goods_forecast.json": _goods_forecast,
    "block_windows.json": _block_windows,
    "resources.json": _resources,
    "dependencies.json": _dependencies,
}


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    out = pathlib.Path(argv[0]) if argv else pathlib.Path("datasets")
    out.mkdir(parents=True, exist_ok=True)
    (out / "meta.json").write_text(
        json.dumps(
            {
                "horizonMinutes": HORIZON_MINUTES,
                "horizonStartIso": HORIZON_START_ISO,
                "corridor": "GZB-ALJN",
                "provenance": "SYNTHETIC - generated by railos_data.generate; not a real IR extract",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    for name, fn in FILES.items():
        rows = [r.model_dump(mode="json") for r in fn()]
        (out / name).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"{name:26s} {len(rows):5d} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
