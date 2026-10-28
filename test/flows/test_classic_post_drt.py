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


def test_post_drt_hold_repair_follows_detailed_routing():
    from librelane.flows.classic import Classic

    ids = [step.id for step in Classic.Steps]
    index = ids.index("OpenROAD.ResizerTimingPostDRT")
    assert ids[index - 2 : index] == [
        "OpenROAD.DetailedRouting",
        "Odb.RemoveRoutingObstructions",
    ]
    assert ids.index("OpenROAD.RCX") > index


def test_post_drt_hold_repair_is_off_by_default():
    from librelane.flows.classic import Classic

    variable = next(
        var for var in Classic.config_vars if var.name == "RUN_POST_DRT_RESIZER_TIMING"
    )
    assert variable.default is False
    assert Classic.gating_config_vars["OpenROAD.ResizerTimingPostDRT"] == [
        "RUN_POST_DRT_RESIZER_TIMING"
    ]


def test_post_drt_hold_repair_extracts_repairs_and_reroutes():
    from librelane.state import DesignFormat
    from librelane.steps import OpenROAD

    step = OpenROAD.ResizerTimingPostDRT
    assert [inner.id for inner in step.Steps] == [
        "OpenROAD.RCX",
        "OpenROAD.ResizerHoldPostDRT",
        "OpenROAD.DetailedRouting",
    ]
    assert DesignFormat.SPEF not in step.outputs


def test_post_drt_hold_repair_script_ships_with_librelane():
    from librelane.common import get_script_dir

    assert os.path.isfile(
        os.path.join(get_script_dir(), "openroad", "rsz_hold_postdrt.tcl")
    )


def test_post_drt_hold_repair_leaves_nets_with_a_rule_alone():
    # the resizer journal cannot undo a change on a net that carries a
    # non-default rule (ODB-0445): such signal nets are made dont-touch during
    # the repair, then released
    from librelane.common import get_script_dir

    with open(
        os.path.join(get_script_dir(), "openroad", "rsz_hold_postdrt.tcl"),
        encoding="utf8",
    ) as f:
        script = f.read()
    protect = script.index("setDoNotTouch 1")
    repair = script.index("log_cmd repair_timing")
    release = script.index("setDoNotTouch 0")
    assert protect < repair < release
    assert "getNonDefaultRule" in script


def test_post_drt_hold_repair_only_legalizes_what_it_changed():
    # incremental detailed placement resets mirrored orientations and pushes
    # neighbours, which would rip up their nets: every unchanged instance is
    # made FIRM while it runs, and the global router listens before it, so
    # that the moved buffers get guides that reach their new pins (DRT-0218)
    from librelane.common import get_script_dir

    with open(
        os.path.join(get_script_dir(), "openroad", "rsz_hold_postdrt.tcl"),
        encoding="utf8",
    ) as f:
        script = f.read()
    guard = script.index("if { [llength $repaired] == 0 }")
    lock = script.index("setPlacementStatus FIRM")
    start = script.index("log_cmd global_route -start_incremental")
    placement = script.index("detailed_placement -incremental")
    end = script.index("log_cmd global_route -end_incremental")
    unlock = script.index("setPlacementStatus PLACED")
    assert guard < lock < start < placement < end < unlock
