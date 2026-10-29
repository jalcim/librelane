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


def _script(name):
    from librelane.common import get_script_dir

    with open(os.path.join(get_script_dir(), "openroad", name), encoding="utf8") as f:
        return f.read()


def test_repair_clock_nets_in_cts_is_off_by_default():
    from librelane.steps import OpenROAD

    variable = next(
        var
        for var in OpenROAD.CTS.config_vars
        if var.name == "CTS_REPAIR_CLOCK_NETS_IN_CTS"
    )
    assert variable.type is bool
    assert variable.default is False


def test_only_the_cts_step_declares_it():
    from librelane.flows.classic import Classic

    owners = [
        step.id
        for step in Classic.Steps
        if any(var.name == "CTS_REPAIR_CLOCK_NETS_IN_CTS" for var in step.config_vars)
    ]
    assert owners == ["OpenROAD.CTS"]


def test_cts_script_passes_the_flag_and_keeps_the_later_repair():
    script = _script("cts.tcl")
    flag = script.index(
        "append_if_flag arg_list CTS_REPAIR_CLOCK_NETS_IN_CTS -repair_clock_nets"
    )
    cts = script.index("log_cmd clock_tree_synthesis {*}$arg_list")
    later = script.index(
        "repair_clock_nets -max_wire_length $::env(CTS_CLK_MAX_WIRE_LENGTH)"
    )
    assert flag < cts < later
