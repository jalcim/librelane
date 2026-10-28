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


def read(*parts):
    from librelane.common import get_script_dir

    root = os.path.dirname(get_script_dir())
    with open(os.path.join(root, *parts), encoding="utf8") as f:
        return f.read()


def test_odbpy_steps_name_their_metrics_file_to_the_script():
    # OpenROAD in python mode never finalizes its logger, so the -metrics file
    # stays unwritten unless the script flushes it by name
    assert "env[\"_LLN_METRICS_OUT\"] = metrics_path" in read("steps", "odb.py")


def test_odbpy_scripts_flush_their_metrics_before_exiting():
    # the reader creates the design after OpenROAD registered its -metrics
    # sink, and metrics then go to a logger without it: the sink is opened
    # again once the reader exists, then flushed at the end
    reader = read("scripts", "odbpy", "reader.py")
    opened = reader.index("utl.open_metrics(metrics_out)")
    flush = reader.index("utl.close_metrics(metrics_out)")
    assert reader.index("OdbReader(input_db") < opened < reader.index("function(**kwargs)") < flush
