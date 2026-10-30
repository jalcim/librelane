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

ROUTING_STEPS = ["GlobalRouting", "RepairDesignPostGRT", "ResizerTimingPostGRT"]


def test_critical_nets_percentage_is_unset_by_default():
    from librelane.steps.common_variables import grt_variables

    variable = next(
        var for var in grt_variables if var.name == "GRT_CRITICAL_NETS_PERCENTAGE"
    )
    assert variable.type == Optional[Decimal]
    assert variable.default is None
    assert variable.units == "%"


def test_every_step_that_routes_declares_it():
    from librelane.steps import OpenROAD

    for name in ROUTING_STEPS:
        step = getattr(OpenROAD, name)
        assert "GRT_CRITICAL_NETS_PERCENTAGE" in [var.name for var in step.config_vars]


def test_global_route_script_passes_the_percentage():
    from librelane.common import get_script_dir

    path = os.path.join(get_script_dir(), "openroad", "common", "grt.tcl")
    with open(path, encoding="utf8") as f:
        script = f.read()
    option = script.index(
        "append_if_exists_argument arg_list GRT_CRITICAL_NETS_PERCENTAGE -critical_nets_percentage"
    )
    assert option < script.index("log_cmd global_route {*}$arg_list")
    assert script.index("set arg_list [list]") < option
