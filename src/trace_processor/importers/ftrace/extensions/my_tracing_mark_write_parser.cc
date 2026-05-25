/*
 * Copyright (C) 2026 The Android Open Source Project
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

#include "src/trace_processor/importers/ftrace/extensions/my_tracing_mark_write_parser.h"

#include <vector>

#include "perfetto/ext/base/string_view.h"

namespace perfetto::trace_processor::ftrace_extensions {

std::vector<SynthesizedEvent> MyTracingMarkWriteParser::Parse(
    const ParserContext& ctx) {
  base::StringView name;
  int32_t event_pid = static_cast<int32_t>(ctx.pid);
  uint32_t type = 0;
  uint64_t value = 0;

  for (const auto& field : ctx.decoded_fields) {
    if (field.name == "name") {
      name = field.as_string();
    } else if (field.name == "pid") {
      event_pid = field.as_int32();
    } else if (field.name == "type") {
      type = field.as_uint32();
    } else if (field.name == "value") {
      value = field.as_uint64();
    }
  }

  std::vector<SynthesizedEvent> results;
  char char_type = static_cast<char>(type);
  SynthesizedEvent ev;
  ev.timestamp_ns = ctx.timestamp;

  if (char_type == 'C') {
    ev.ftrace_event_bytes = EncodeAtraceCounterEvent(
        static_cast<uint32_t>(event_pid), name, static_cast<int64_t>(value));
    results.push_back(std::move(ev));
  } else if (char_type == 'B') {
    ev.ftrace_event_bytes =
        EncodeAtraceBeginEvent(static_cast<uint32_t>(event_pid), name);
    results.push_back(std::move(ev));
  } else if (char_type == 'E') {
    ev.ftrace_event_bytes =
        EncodeAtraceEndEvent(static_cast<uint32_t>(event_pid));
    results.push_back(std::move(ev));
  }

  return results;
}

}  // namespace perfetto::trace_processor::ftrace_extensions
