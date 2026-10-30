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
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

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


def _without(*prefixes: str) -> str:
    return "".join(
        line
        for line in _DEF.splitlines(keepends=True)
        if not line.strip().startswith(prefixes)
    )


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


def _run_tclsh(step_dir: Path, def_in: Path) -> subprocess.CompletedProcess:
    tclsh = shutil.which("tclsh")
    if tclsh is None:
        pytest.skip("tclsh not found")
    read_tcl = SCRIPTS / "magic" / "common" / "read.tcl"
    script = _write(
        step_dir / "tcl" / "run.tcl",
        f"source {{{read_tcl}}}\nputs [def_without_fills {{{def_in}}}]\n",
    )
    return subprocess.run(
        [tclsh, str(script)],
        capture_output=True,
        text=True,
        env={**os.environ, "STEP_DIR": str(step_dir)},
    )


def _def_without_fills(tmp_path: Path, source: Optional[Path] = None) -> Path:
    if source is None:
        source = _write(tmp_path / "source" / "filled.def", _DEF)
    result = _run_tclsh(tmp_path, source)
    assert result.returncode == 0, result.stderr
    return Path(result.stdout.splitlines()[-1])


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


def test_read_def_leaves_the_fills_section_out(tmp_path: Path):
    copy = _def_without_fills(tmp_path)
    text = copy.read_text(encoding="utf-8")
    assert copy.parent == tmp_path
    assert "FILLS" not in text
    assert "DIEAREA ( 0 0 ) ( 100000 100000 ) ;" in text
    assert text.endswith("END DESIGN\n")


def test_read_def_keeps_a_def_without_fills(tmp_path: Path):
    source = _write(
        tmp_path / "source" / "plain.def", _without("FILLS", "- LAYER", "END FILLS")
    )
    assert _def_without_fills(tmp_path, source) == source
    assert not list(tmp_path.glob("*.nofills.def"))


def test_an_unclosed_fills_section_stops_magic(tmp_path: Path):
    source = _write(tmp_path / "source" / "unclosed.def", _without("END FILLS"))
    result = _run_tclsh(tmp_path, source)
    assert result.returncode == 1
    assert "never closes it" in result.stderr
