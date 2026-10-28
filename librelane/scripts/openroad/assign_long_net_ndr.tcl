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

# Crosstalk mitigation for an open-source flow without signal integrity
# analysis: every signal net whose pins span a half-perimeter of at least
# LONG_NET_NDR_MIN_HPWL gets a wider-spacing non-default rule right before
# detailed routing, which keeps its neighbours further away. It runs after the
# last resizer step, whose journal cannot undo a net rule change (ODB-0445).
# Nets that already carry a rule, such as the clock nets given one by CTS, keep
# it.
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb

set block [ord::get_db_block]
set dbu [[[ord::get_db] getTech] getDbUnitsPerMicron]
set rule_name "lln_long_net_spacing"
set rule [$block findNonDefaultRule $rule_name]
if { $rule eq "NULL" } {
    log_cmd create_ndr -name $rule_name -spacing $::env(LONG_NET_NDR_SPACING)
    set rule [$block findNonDefaultRule $rule_name]
}

set threshold [expr { $::env(LONG_NET_NDR_MIN_HPWL) * $dbu }]
set assigned 0
foreach net [$block getNets] {
    if { [$net isSpecial] || [$net getSigType] in {POWER GROUND} } {
        continue
    }
    if { [$net getNonDefaultRule] ne "NULL" } {
        continue
    }
    set box [$net getTermBBox]
    if { [$box dx] + [$box dy] >= $threshold } {
        $net setNonDefaultRule $rule
        incr assigned
    }
}
puts "\[INFO\] Assigned '$rule_name' ($::env(LONG_NET_NDR_SPACING) spacing) to $assigned nets of at least $::env(LONG_NET_NDR_MIN_HPWL) µm half-perimeter."
write_metric_int "route__long_net_ndr__count" $assigned

write_views
