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
import resource
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

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
SPECIALNETS 1 ;
    - FILLS + USE POWER ;
END SPECIALNETS
NETS 1 ;
    - n1 ;
END NETS
END DESIGN
"""


def _macro_lef(*names: str) -> str:
    # No FOREIGN: KLayout then draws the LEF view into the cell, which
    # stream_out.py must clear like any library cell.
    macros = "".join(
        f"MACRO {name}\n"
        "  CLASS CORE ;\n"
        "  ORIGIN 0 0 ;\n"
        "  SIZE 4 BY 4 ;\n"
        "  PIN A\n"
        "    DIRECTION INPUT ;\n"
        "    PORT\n"
        "      LAYER Metal2 ;\n"
        "        RECT 0 0 1 1 ;\n"
        "    END\n"
        "  END A\n"
        "  OBS\n"
        "    LAYER Metal2 ;\n"
        "      RECT 2 2 3 3 ;\n"
        "  END\n"
        f"END {name}\n"
        for name in names
    )
    return (
        f'VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n{macros}END LIBRARY\n'
    )


def _without(*prefixes: str) -> str:
    return "".join(
        line
        for line in _DEF.splitlines(keepends=True)
        if not line.strip().startswith(prefixes)
    )


def _without_fills() -> str:
    return _without("FILLS", "- LAYER", "END FILLS")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _stream_out(
    tmp_path: Path, def_text: str = _DEF, extra: Sequence[str] = ()
) -> Path:
    if not PDK.is_dir():
        pytest.skip(f"PDK not found: {PDK}")
    tech = PDK / "libs.tech" / "klayout" / "tech"
    tech_lef = PDK / "libs.ref" / "sg13cmos5l_stdcell" / "lef" / "sg13cmos5l_tech.lef"
    def_in = _write(tmp_path / "filled.def", def_text)
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
            *extra,
        ],
        check=True,
    )
    return gds


def _run_tclsh(
    step_dir: Path, def_in: Path, file_size_limit: Optional[int] = None
) -> subprocess.CompletedProcess:
    tclsh = shutil.which("tclsh")
    if tclsh is None:
        pytest.skip("tclsh not found")
    read_tcl = SCRIPTS / "magic" / "common" / "read.tcl"
    script = _write(
        step_dir / "tcl" / "run.tcl",
        f"source {{{read_tcl}}}\nputs [def_without_fills {{{def_in}}}]\n",
    )

    def limit_file_size() -> None:
        if file_size_limit is not None:
            # SIGXFSZ would kill tclsh. Ignored, the write fails with EFBIG.
            signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
            limit = (file_size_limit, file_size_limit)
            resource.setrlimit(resource.RLIMIT_FSIZE, limit)

    return subprocess.run(
        [tclsh, str(script)],
        capture_output=True,
        text=True,
        env={**os.environ, "STEP_DIR": str(step_dir)},
        preexec_fn=limit_file_size,
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


def test_stream_out_clears_a_library_cell_named_like_a_fill_cell(tmp_path: Path):
    kdb = pytest.importorskip("klayout.db")
    names = ("spare_DEF_FILL", "spare_twin")
    library = kdb.Layout()
    for name in names:
        cell = library.create_cell(name)
        cell.shapes(library.layer(10, 0)).insert(kdb.Box(0, 0, 4000, 4000))
    spare_gds = tmp_path / "spare.gds"
    library.write(str(spare_gds))
    spare_lef = _write(tmp_path / "spare.lef", _macro_lef(*names))
    placed = _DEF.replace(
        "FILLS 4 ;",
        "COMPONENTS 2 ;\n"
        "    - a spare_DEF_FILL + PLACED ( 50000 50000 ) N ;\n"
        "    - b spare_twin + PLACED ( 60000 50000 ) N ;\n"
        "END COMPONENTS\n"
        "FILLS 4 ;",
    )
    gds = _stream_out(
        tmp_path,
        placed,
        ["--input-lef", str(spare_lef), "--with-gds-file", str(spare_gds)],
    )
    layout = kdb.Layout()
    layout.read(str(gds))
    spare, twin = (
        sorted(
            (
                layout.get_info(index).layer,
                layout.get_info(index).datatype,
                str(shape.box),
            )
            for index in layout.layer_indexes()
            for shape in layout.cell(name).shapes(index).each()
        )
        for name in names
    )
    assert spare == twin


def test_read_def_leaves_the_fills_section_out(tmp_path: Path):
    copy = _def_without_fills(tmp_path)
    assert copy.parent == tmp_path
    assert copy.read_text(encoding="utf-8") == _without_fills()


def test_read_def_keeps_a_def_without_fills(tmp_path: Path):
    source = _write(tmp_path / "source" / "plain.def", _without_fills())
    assert _def_without_fills(tmp_path, source) == source
    assert not list(tmp_path.glob("*.nofills.def"))


def test_read_def_accepts_a_comment_after_end_fills(tmp_path: Path):
    source = _write(
        tmp_path / "source" / "commented.def",
        _DEF.replace("END FILLS\n", "END FILLS # end of the fill\n"),
    )
    copy = _def_without_fills(tmp_path, source)
    assert copy.parent == tmp_path
    assert copy.read_text(encoding="utf-8") == _without_fills()


def test_an_unclosed_fills_section_is_read_as_is(tmp_path: Path):
    source = _write(tmp_path / "source" / "unclosed.def", _without("END FILLS"))
    assert _def_without_fills(tmp_path, source) == source
    assert not list(tmp_path.glob("*.nofills.def"))


def test_read_def_keeps_crlf_line_endings(tmp_path: Path):
    source = _write(tmp_path / "source" / "crlf.def", _DEF.replace("\n", "\r\n"))
    copy = _def_without_fills(tmp_path, source)
    assert copy.read_bytes() == _without_fills().replace("\n", "\r\n").encode()


def test_a_failed_copy_leaves_nothing_in_step_dir(tmp_path: Path):
    source = _write(tmp_path / "source" / "filled.def", _DEF)
    result = _run_tclsh(tmp_path, source, file_size_limit=64)
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.splitlines()[-1]) == source
    assert not list(tmp_path.glob("*.nofills.def"))
