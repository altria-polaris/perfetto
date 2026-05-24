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

#ifndef SRC_TRACE_PROCESSOR_IMPORTERS_FTRACE_EXTENSIONS_FTRACE_EXTENSION_PARSER_H_
#define SRC_TRACE_PROCESSOR_IMPORTERS_FTRACE_EXTENSIONS_FTRACE_EXTENSION_PARSER_H_

#include <cstdint>
#include <string>
#include <utility>
#include <vector>

#include "perfetto/ext/base/string_view.h"
#include "perfetto/protozero/proto_decoder.h"
#include "perfetto/trace_processor/ref_counted.h"
#include "perfetto/trace_processor/trace_blob_view.h"
#include "src/trace_processor/importers/proto/packet_sequence_state_generation.h"
#include "src/trace_processor/storage/trace_storage.h"

namespace perfetto::trace_processor {

class TraceProcessorContext;

namespace ftrace_extensions {

// Represents a decoded field value from a generic ftrace event.
struct DecodedField {
  uint32_t field_id = 0;
  base::StringView name;

  int64_t as_int64() const;
  int32_t as_int32() const;
  uint32_t as_uint32() const;
  uint64_t as_uint64() const;
  base::StringView as_string() const;

  enum class Type {
    kInt64,
    kInt32,
    kUint32,
    kUint64,
    kString
  } type = Type::kInt64;
  union {
    int64_t int64_val = 0;
    int32_t int32_val;
    uint32_t uint32_val;
    uint64_t uint64_val;
  };
  base::StringView string_val;
};

// Represents a synthesized event to be pushed to the sorter.
struct SynthesizedEvent {
  int64_t timestamp_ns = 0;
  std::vector<uint8_t> ftrace_event_bytes;
};

// Context passed to parsers during Parse().
struct ParserContext {
  TraceProcessorContext* context = nullptr;
  uint32_t cpu = 0;
  RefPtr<PacketSequenceStateGeneration> sequence_state;
  std::vector<DecodedField> decoded_fields;
  StringId event_name = kNullStringId;
  uint32_t pid = 0;
};

// Base class for custom ftrace event parsers.
//
// Inherit from this class to implement a parser for a specific generic ftrace
// event (e.g. "ggo"). Register your implementation via FtraceExtensionRegistry.
class FtraceExtensionParser {
 public:
  virtual ~FtraceExtensionParser();

  virtual base::StringView GetEventName() const = 0;

  virtual bool CanParse(base::StringView event_name) {
    return event_name == GetEventName();
  }

  virtual std::vector<SynthesizedEvent> Parse(const ParserContext& ctx) = 0;

 protected:
  static int64_t AdjustTimestampWithField(
      int64_t base_ts,
      base::StringView offset_field_name,
      const std::vector<DecodedField>& fields);

  static std::vector<uint8_t> EncodeAtraceCounterEvent(uint32_t pid,
                                                       base::StringView name,
                                                       int64_t value);

  static std::vector<uint8_t> EncodeAtraceBeginEvent(uint32_t pid,
                                                     base::StringView name);

  static std::vector<uint8_t> EncodeAtraceEndEvent(uint32_t pid);
};

}  // namespace ftrace_extensions
}  // namespace perfetto::trace_processor

#endif  // SRC_TRACE_PROCESSOR_IMPORTERS_FTRACE_EXTENSIONS_FTRACE_EXTENSION_PARSER_H_
