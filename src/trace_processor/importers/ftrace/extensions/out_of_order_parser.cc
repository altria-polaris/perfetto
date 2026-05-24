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

#include "src/trace_processor/importers/ftrace/extensions/out_of_order_parser.h"

#include <vector>

#include "perfetto/ext/base/string_utils.h"

namespace perfetto::trace_processor::ftrace_extensions {

namespace {
// Global state to simulate passing data from Event B to Event A.
// This is used for the out-of-order trace processing test.
int64_t g_base_ts = 0;
}  // namespace

EventBParser::~EventBParser() = default;
EventAParser::~EventAParser() = default;

std::vector<SynthesizedEvent> EventBParser::Parse(const ParserContext& ctx) {
  for (const auto& field : ctx.decoded_fields) {
    if (field.name == "base_ts") {
      g_base_ts = field.as_int64();
      break;
    }
  }
  // Event B produces no synthesized events itself.
  return {};
}

std::vector<SynthesizedEvent> EventAParser::Parse(const ParserContext& ctx) {
  int64_t offsets[8] = {0};
  int32_t values[8] = {0};
  base::StringView names[8];

  // Decode the 24 fields (8 offsets, 8 values, 8 names).
  for (const auto& field : ctx.decoded_fields) {
    if (field.name.size() > 3 && field.name.substr(0, 3) == "off") {
      int idx = field.name.at(3) - '1';
      if (idx >= 0 && idx < 8)
        offsets[idx] = field.as_int64();
    } else if (field.name.size() > 3 && field.name.substr(0, 3) == "val") {
      int idx = field.name.at(3) - '1';
      if (idx >= 0 && idx < 8)
        values[idx] = field.as_int32();
    } else if (field.name.size() > 4 && field.name.substr(0, 4) == "name") {
      int idx = field.name.at(4) - '1';
      if (idx >= 0 && idx < 8)
        names[idx] = field.as_string();
    }
  }

  std::vector<SynthesizedEvent> results;
  // Synthesize events. We iterate 0 to 7 to generate them sequentially.
  for (int i = 0; i < 8; ++i) {
    if (names[i].empty())
      continue;

    SynthesizedEvent ev;
    // CRITICAL: Generate the timestamp out-of-order backwards in time!
    ev.timestamp_ns = g_base_ts - offsets[i];
    ev.ftrace_event_bytes =
        EncodeAtraceCounterEvent(ctx.pid, names[i], values[i]);
    results.push_back(std::move(ev));
  }

  return results;
}

}  // namespace perfetto::trace_processor::ftrace_extensions
