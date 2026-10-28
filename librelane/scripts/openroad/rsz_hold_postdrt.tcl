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

# Final hold repair on extracted parasitics, after detailed routing.
#
# Nets that are left untouched keep the parasitics read from the SPEF files of
# every resizer corner, nets edited by the resizer are estimated from their
# incremental global routes. Every net attached to an instance that was added,
# resized or moved by the repair or by detailed placement is ripped up and gets
# new guides, so that the detailed router that follows reroutes it.
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl

read_current_odb

set_propagated_clock [all_clocks]

set_dont_touch_objects

source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
source $::env(SCRIPTS_DIR)/openroad/common/set_routing_layers.tcl
source $::env(SCRIPTS_DIR)/openroad/common/set_layer_adjustments.tcl
set_macro_extension $::env(GRT_MACRO_EXTENSION)

foreach pair $::env(_RSZ_SPEFS) {
    set corner_name [lindex $pair 0]
    set spef [lindex $pair 1]
    puts "Reading parasitics for the '$corner_name' corner at '$spef'…"
    read_spef -corner $corner_name $spef
}

proc lln_instance_key {inst} {
    return [list {*}[$inst getLocation] [$inst getOrient] [[$inst getMaster] getName]]
}

proc lln_instance_snapshot {block} {
    set snapshot [dict create]
    foreach inst [$block getInsts] {
        dict set snapshot [$inst getName] [lln_instance_key $inst]
    }
    return $snapshot
}

proc lln_changed_instances {block snapshot} {
    set changed [list]
    foreach inst [$block getInsts] {
        set name [$inst getName]
        if { ![dict exists $snapshot $name] } {
            lappend changed $inst
            continue
        }
        if { [lln_instance_key $inst] ne [dict get $snapshot $name] } {
            lappend changed $inst
        }
    }
    return $changed
}

proc lln_signal_nets {instances} {
    set nets [dict create]
    foreach inst $instances {
        foreach iterm [$inst getITerms] {
            set net [$iterm getNet]
            if { $net eq "NULL" } {
                continue
            }
            if { [$net getSigType] in {POWER GROUND} || [$net isSpecial] } {
                continue
            }
            dict set nets [$net getName] $net
        }
    }
    return [dict values $nets]
}

set block [ord::get_db_block]
set snapshot [lln_instance_snapshot $block]

set hold_args [list]
lappend hold_args -verbose
lappend hold_args -hold
lappend hold_args -setup_margin $::env(DRT_RESIZER_SETUP_SLACK_MARGIN)
lappend hold_args -hold_margin $::env(DRT_RESIZER_HOLD_SLACK_MARGIN)
lappend hold_args -max_buffer_percent $::env(DRT_RESIZER_HOLD_MAX_BUFFER_PCT)
append_if_flag hold_args DRT_RESIZER_ALLOW_SETUP_VIOS -allow_setup_violations

log_cmd repair_timing {*}$hold_args

# Legalize the inserted buffers incrementally, leaving every legal cell where
# it is and as it is mirrored, with the global router listening, then mark the
# nets of every added, resized, moved or flipped instance dirty so they get
# guides.
log_cmd global_route -start_incremental
source $::env(SCRIPTS_DIR)/openroad/common/dpl_cell_pad.tcl
log_cmd detailed_placement -incremental\
    -max_displacement [subst { $::env(PL_MAX_DISPLACEMENT_X) $::env(PL_MAX_DISPLACEMENT_Y) }]
check_placement -verbose
set changed [lln_changed_instances $block $snapshot]
set dirty [lln_signal_nets $changed]
foreach net $dirty {
    foreach iterm [$net getITerms] {
        if { [$iterm isOutputSignal] } {
            $iterm disconnect
            $iterm connect $net
        }
    }
}
log_cmd global_route -end_incremental

set ripped 0
foreach net $dirty {
    set wire [$net getWire]
    if { $wire ne "NULL" } {
        odb::dbWire_destroy $wire
        incr ripped
    }
}
puts "\[INFO\] [llength $changed] instances added, resized, moved or flipped, $ripped nets ripped up for rerouting."
write_metric_int "route__hold_repair_postdrt__instance__count" [llength $changed]
write_metric_int "route__hold_repair_postdrt__ripped_net__count" $ripped

unset_dont_touch_objects

write_views
