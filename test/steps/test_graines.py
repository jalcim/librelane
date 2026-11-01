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
from decimal import Decimal
from typing import Optional

PLACEMENT = {
    "PL_RANDOM_SEED": Optional[int],
    "PL_PERTURB_DIST": Optional[Decimal],
    "PL_FILLER_SEED": Optional[int],
}
ROUTING = {
    "GRT_RANDOM_SEED": Optional[int],
    "GRT_CAPACITY_PERTURBATION_PCT": Optional[Decimal],
    "GRT_PERTURBATION_AMOUNT": Optional[int],
}
ROUTING_STEPS = ["GlobalRouting", "RepairDesignPostGRT", "ResizerTimingPostGRT"]
WARNING = "GRT_CAPACITY_PERTURBATION_PCT and GRT_PERTURBATION_AMOUNT are ignored: GRT_RANDOM_SEED is unset."


def _script(name):
    from librelane.common import get_script_dir

    with open(os.path.join(get_script_dir(), "openroad", name), encoding="utf8") as f:
        return f.read()


def _variable(step, name):
    return next(var for var in step.config_vars if var.name == name)


def test_placement_seeds_are_unset_by_default():
    from librelane.steps import OpenROAD

    for step in [OpenROAD.GlobalPlacement, OpenROAD.GlobalPlacementSkipIO]:
        for name, kind in PLACEMENT.items():
            variable = _variable(step, name)
            assert variable.type == kind
            assert variable.default is None
        assert _variable(step, "PL_PERTURB_DIST").units == "nm"


def test_placement_script_passes_each_seed():
    script = _script("gpl.tcl")
    start = script.index("set arg_list [list]")
    call = script.index("log_cmd global_placement {*}$arg_list")
    for name, option in [
        ("PL_RANDOM_SEED", "-random_seed"),
        ("PL_PERTURB_DIST", "-perturb_dist"),
        ("PL_FILLER_SEED", "-filler_seed"),
    ]:
        line = script.index(f"append_if_exists_argument arg_list {name} {option}")
        assert start < line < call


def test_routing_seeds_are_unset_by_default():
    from librelane.steps.common_variables import grt_variables

    for name, kind in ROUTING.items():
        variable = next(var for var in grt_variables if var.name == name)
        assert variable.type == kind
        assert variable.default is None
    percentage = next(
        var for var in grt_variables if var.name == "GRT_CAPACITY_PERTURBATION_PCT"
    )
    assert percentage.units == "%"


def test_every_step_that_routes_declares_them():
    from librelane.steps import OpenROAD

    for step_name in ROUTING_STEPS:
        step = getattr(OpenROAD, step_name)
        names = [var.name for var in step.config_vars]
        for name in ROUTING:
            assert name in names, f"{name} missing from OpenROAD.{step_name}"


def test_global_route_script_sets_the_random_router_only_with_a_seed():
    script = _script(os.path.join("common", "grt.tcl"))
    guard = script.index("if { [info exists ::env(GRT_RANDOM_SEED)] } {")
    call = script.index("log_cmd set_global_routing_random {*}$random_args")
    assert (
        guard
        < call
        < script.index("} elseif {")
        < script.index(WARNING)
        < script.index("log_cmd global_route {*}$arg_list")
    )


def test_detailed_routing_seeds_are_unset_by_default():
    from librelane.steps import OpenROAD

    for name, kind in [("DRT_OR_SEED", Optional[int]), ("DRT_OR_K", Optional[Decimal])]:
        variable = _variable(OpenROAD.DetailedRouting, name)
        assert variable.type == kind
        assert variable.default is None


def test_detailed_route_script_drops_the_hard_coded_42():
    script = _script("drt.tcl")
    assert "-or_seed 42" not in script
    assert "lappend drt_args -or_seed" not in script
    seed = script.index("append_if_exists_argument drt_args DRT_OR_SEED -or_seed")
    or_k = script.index("append_if_exists_argument drt_args DRT_OR_K -or_k")
    assert seed < or_k < script.index("drt_run $i {*}$drt_args")
