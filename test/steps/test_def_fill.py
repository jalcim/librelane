# Copyright 2026 The LibreLane Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "librelane" / "scripts"
PDK = Path("/opt/nebula-eda/IHP-Open-PDK/ihp-sg13cmos5l")

_DEF = """VERSION 5.8 ;
DIVIDERCHAR "/" ;
BUSBITCHARS "[]" ;
DESIGN filled ;
UNITS DISTANCE MICRONS 1000 ;
DIEAREA ( 0 0 ) ( 100000 100000 ) ;
FILLS 4 ;
    - LAYER Metal2 RECT ( 0 0 ) ( 5000 2000 ) ;
    - LAYER Metal2 RECT ( 10000 0 ) ( 15000 2000 ) ;
    - LAYER Metal2 RECT ( 20000 0 ) ( 25000 2000 ) ;
    - LAYER Metal2 RECT ( 30000 0 ) ( 35000 2000 ) ;
END FILLS
END DESIGN
"""


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _stream_out(tmp_path: Path) -> Path:
    if not PDK.is_dir():
        pytest.skip(f"PDK not found: {PDK}")
    tech = PDK / "libs.tech" / "klayout" / "tech"
    tech_lef = PDK / "libs.ref" / "sg13cmos5l_stdcell" / "lef" / "sg13cmos5l_tech.lef"
    def_in = _write(tmp_path / "filled.def", _DEF)
    gds = tmp_path / "filled.gds"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "klayout" / "stream_out.py"),
            str(def_in),
            "--output",
            str(gds),
            "--top",
            "filled",
            "--lyt",
            str(tech / "sg13cmos5l.lyt"),
            "--lyp",
            str(tech / "sg13cmos5l.lyp"),
            "--lym",
            str(tech / "sg13cmos5l.map"),
            "--input-lef",
            str(tech_lef),
        ],
        check=True,
    )
    return gds


def test_stream_out_keeps_the_def_fill_cell(tmp_path: Path):
    kdb = pytest.importorskip("klayout.db")
    gds = _stream_out(tmp_path)
    layout = kdb.Layout()
    layout.read(str(gds))
    fill = layout.cell("filled_DEF_FILL")
    assert fill is not None
    metal2_fill = layout.find_layer(10, 22)
    count = 0 if metal2_fill is None else fill.shapes(metal2_fill).size()
    assert count == 4
