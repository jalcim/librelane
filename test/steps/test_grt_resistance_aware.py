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
import re
from decimal import Decimal
from typing import Optional

ROUTING_STEPS = ["GlobalRouting", "RepairDesignPostGRT", "ResizerTimingPostGRT"]


def _grt_script():
    from librelane.common import get_script_dir

    path = os.path.join(get_script_dir(), "openroad", "common", "grt.tcl")
    with open(path, encoding="utf8") as f:
        return f.read()


def test_resistance_aware_routing_is_off_by_default():
    from librelane.steps.common_variables import grt_variables

    variables = {var.name: var for var in grt_variables}
    flag = variables["GRT_RESISTANCE_AWARE"]
    percentage = variables["GRT_RES_AWARE_NETS_PERCENTAGE"]
    assert flag.type is bool and flag.default is False
    assert percentage.type == Optional[Decimal]
    assert percentage.default is None
    assert percentage.units == "%"


def test_every_step_that_routes_declares_both():
    from librelane.steps import OpenROAD

    for name in ROUTING_STEPS:
        names = [var.name for var in getattr(OpenROAD, name).config_vars]
        assert "GRT_RESISTANCE_AWARE" in names
        assert "GRT_RES_AWARE_NETS_PERCENTAGE" in names


def test_global_route_script_passes_both_options():
    script = _grt_script()
    flag = script.index("append_if_flag arg_list GRT_RESISTANCE_AWARE -resistance_aware")
    percentage = script.index(
        "append_if_exists_argument arg_list GRT_RES_AWARE_NETS_PERCENTAGE -res_aware_nets_percentage"
    )
    assert flag < percentage < script.index("log_cmd global_route {*}$arg_list")
    assert script.index("set arg_list [list]") < flag


def test_only_the_common_script_calls_global_route():
    # global_route resets -resistance_aware on every call it is not given, an
    # incremental call elsewhere would drop it for the rest of its step
    from librelane.common import get_script_dir

    root = get_script_dir()
    call = re.compile(r"^\s*(log_cmd\s+)?global_route\b")
    callers = set()
    for folder, _, files in os.walk(root):
        for name in files:
            if name.endswith(".tcl"):
                path = os.path.join(folder, name)
                with open(path, encoding="utf8") as f:
                    if any(call.match(line) for line in f):
                        callers.add(os.path.relpath(path, root))
    assert callers == {os.path.join("openroad", "common", "grt.tcl")}
