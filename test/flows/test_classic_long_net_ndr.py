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


def test_long_net_rule_comes_after_the_last_resizer_step_before_detailed_routing():
    # the resizer journal cannot undo a net rule change (ODB-0445), so no
    # resizer step may run on nets that carry the rule
    from librelane.flows.classic import Classic

    ids = [step.id for step in Classic.Steps]
    index = ids.index("OpenROAD.AssignLongNetNDR")
    assert ids[index + 1] == "OpenROAD.DetailedRouting"
    assert ids.index("OpenROAD.ResizerTimingPostGRT") < index


def test_long_net_rule_is_off_by_default():
    from librelane.flows.classic import Classic

    variable = next(var for var in Classic.config_vars if var.name == "RUN_LONG_NET_NDR")
    assert variable.default is False
    assert Classic.gating_config_vars["OpenROAD.AssignLongNetNDR"] == ["RUN_LONG_NET_NDR"]


def test_long_net_rule_defaults_to_double_spacing_from_one_millimetre():
    from librelane.steps import OpenROAD

    defaults = {var.name: var.default for var in OpenROAD.AssignLongNetNDR.config_vars}
    assert defaults["LONG_NET_NDR_MIN_HPWL"] == 1000
    assert defaults["LONG_NET_NDR_SPACING"] == "*2"


def test_long_net_rule_script_ships_with_librelane():
    from librelane.common import get_script_dir

    assert os.path.isfile(os.path.join(get_script_dir(), "openroad", "assign_long_net_ndr.tcl"))
