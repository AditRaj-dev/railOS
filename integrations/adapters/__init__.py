from .protocol import (
    BDMSAdapter, COAAdapter, GoodsAdapter, SMMSAdapter, SourceAdapter,
    SyntheticAdapter, TDMSAdapter, TMSAdapter, TimetableAdapter,
)

ADAPTERS = {
    "tms": TMSAdapter("TMS"),
    "smms": SMMSAdapter("SMMS"),
    "tdms": TDMSAdapter("TDMS"),
    "coa": COAAdapter("COA"),
    "bdms": BDMSAdapter("BDMS"),
    "timetable": TimetableAdapter("TIMETABLE"),
    "goods": GoodsAdapter("GOODS"),
}

__all__ = ["ADAPTERS", "SourceAdapter", "SyntheticAdapter"]
