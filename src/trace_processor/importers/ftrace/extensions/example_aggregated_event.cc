/*
 * Copyright (C) 2025 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "src/trace_processor/importers/ftrace/extensions/example_aggregated_event.h"

#include <vector>

#include "perfetto/ext/base/string_utils.h"
#include "perfetto/ext/base/string_view.h"

namespace perfetto::trace_processor::ftrace_extensions {

std::vector<SynthesizedEvent> ExampleAggregatedEvent::Parse(
    const ParserContext& ctx) {
  int64_t base_ts = 0;
  int64_t offsets[4] = {0, 0, 0, 0};
  int32_t values[4] = {0, 0, 0, 0};

  // Decode fields from the generic event payload.
  // We use field names to remain compatible across different Android versions.
  for (const auto& field : ctx.decoded_fields) {
    if (field.name == "base_timestamp") {
      base_ts = field.as_int64();
    } else if (field.name == "ts1") {
      offsets[0] = field.as_int64();
    } else if (field.name == "ts2") {
      offsets[1] = field.as_int64();
    } else if (field.name == "ts3") {
      offsets[2] = field.as_int64();
    } else if (field.name == "ts4") {
      offsets[3] = field.as_int64();
    } else if (field.name == "val1") {
      values[0] = field.as_int32();
    } else if (field.name == "val2") {
      values[1] = field.as_int32();
    } else if (field.name == "val3") {
      values[2] = field.as_int32();
    } else if (field.name == "val4") {
      values[3] = field.as_int32();
    }
  }

  std::vector<SynthesizedEvent> results;
  for (int i = 0; i < 4; ++i) {
    SynthesizedEvent ev;
    ev.timestamp_ns = base_ts + offsets[i];

    // Create a descriptive name for the counter.
    base::StackString<64> counter_name("example_counter_%d", i);

    // Encode as a standard atrace counter event.
    ev.ftrace_event_bytes = EncodeAtraceCounterEvent(
        ctx.pid, counter_name.string_view(), values[i]);
    results.push_back(std::move(ev));
  }

  return results;
}

}  // namespace perfetto::trace_processor::ftrace_extensions
