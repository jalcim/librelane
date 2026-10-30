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

WARNING = "PL_ROUTABILITY_INFLATION_RATIO_COEF is ignored: PL_ROUTABILITY_DRIVEN is off."
ELSE_BRANCH = "} elseif { [info exists ::env(PL_ROUTABILITY_INFLATION_RATIO_COEF)] } {"


def _script(name):
    from librelane.common import get_script_dir

    with open(os.path.join(get_script_dir(), "openroad", name), encoding="utf8") as f:
        return f.read()


def test_inflation_ratio_coefficient_is_unset_by_default():
    from librelane.steps import OpenROAD

    variable = next(
        var
        for var in OpenROAD.GlobalPlacement.config_vars
        if var.name == "PL_ROUTABILITY_INFLATION_RATIO_COEF"
    )
    assert variable.type == Optional[Decimal]
    assert variable.default is None


def test_only_the_global_placement_step_declares_it():
    from librelane.flows.classic import Classic

    owners = [
        step.id
        for step in Classic.Steps
        if any(
            var.name == "PL_ROUTABILITY_INFLATION_RATIO_COEF" for var in step.config_vars
        )
    ]
    assert owners == ["OpenROAD.GlobalPlacement"]


def test_placement_script_passes_it_in_routability_mode():
    script = _script("gpl.tcl")
    mode = script.index("lappend arg_list -routability_driven")
    option = script.index(
        "append_if_exists_argument arg_list PL_ROUTABILITY_INFLATION_RATIO_COEF -routability_inflation_ratio_coef"
    )
    assert mode < option < script.index("log_cmd global_placement {*}$arg_list")
    assert option < script.index(ELSE_BRANCH)


def test_placement_script_warns_when_routability_is_off():
    script = _script("gpl.tcl")
    option = script.index("PL_ROUTABILITY_INFLATION_RATIO_COEF -routability_inflation_ratio_coef")
    assert option < script.index(WARNING) < script.index("log_cmd global_placement")
    assert script.index(ELSE_BRANCH) < script.index(WARNING)
