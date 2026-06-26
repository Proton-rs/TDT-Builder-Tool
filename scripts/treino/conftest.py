import sys, pathlib

_here = pathlib.Path(__file__).resolve().parent
_root = _here.parents[1]
for _p in (_here, _root / "src", _root / "scripts" / "enriquecer_v5"):
    sys.path.insert(0, str(_p))
