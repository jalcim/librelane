# Copyright 2022-2023 Efabless Corporation
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
if { ![info exists ::grt_preamble] } {
    set ::grt_preamble 1

    source $::env(SCRIPTS_DIR)/openroad/common/set_routing_layers.tcl
    source $::env(SCRIPTS_DIR)/openroad/common/set_layer_adjustments.tcl

    set_macro_extension $::env(GRT_MACRO_EXTENSION)
}

set arg_list [list]
lappend arg_list -congestion_iterations $::env(GRT_OVERFLOW_ITERS)
lappend arg_list -verbose
append_if_flag arg_list GRT_ALLOW_CONGESTION -allow_congestion

if { [info exists ::env(GRT_RANDOM_SEED)] } {
    set random_args [list -seed $::env(GRT_RANDOM_SEED)]
    append_if_exists_argument random_args GRT_CAPACITY_PERTURBATION_PCT -capacities_perturbation_percentage
    append_if_exists_argument random_args GRT_PERTURBATION_AMOUNT -perturbation_amount
    log_cmd set_global_routing_random {*}$random_args
} elseif { [info exists ::env(GRT_CAPACITY_PERTURBATION_PCT)] || [info exists ::env(GRT_PERTURBATION_AMOUNT)] } {
    puts "\[WARNING\] GRT_CAPACITY_PERTURBATION_PCT and GRT_PERTURBATION_AMOUNT are ignored: GRT_RANDOM_SEED is unset."
}

log_cmd global_route {*}$arg_list

write_guides $::env(STEP_DIR)/after_grt.guide
