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

#include "src/trace_processor/importers/ftrace/extensions/ftrace_extension_parser.h"

#include <cstdint>
#include <vector>

#include "perfetto/ext/base/string_utils.h"
#include "perfetto/protozero/scattered_heap_buffer.h"
#include "protos/perfetto/trace/ftrace/ftrace.pbzero.h"
#include "protos/perfetto/trace/ftrace/ftrace_event.pbzero.h"
#include "src/trace_processor/types/trace_processor_context.h"

namespace perfetto::trace_processor {
namespace ftrace_extensions {

FtraceExtensionParser::~FtraceExtensionParser() = default;

int64_t DecodedField::as_int64() const {
  switch (type) {
    case Type::kInt64:
      return int64_val;
    case Type::kInt32:
      return int32_val;
    case Type::kUint32:
      return uint32_val;
    case Type::kUint64:
      return static_cast<int64_t>(uint64_val);
    case Type::kString:
      break;
  }
  return 0;
}

int32_t DecodedField::as_int32() const {
  return static_cast<int32_t>(as_int64());
}

uint32_t DecodedField::as_uint32() const {
  switch (type) {
    case Type::kUint32:
      return uint32_val;
    case Type::kInt32:
      return static_cast<uint32_t>(int32_val);
    case Type::kInt64:
      return static_cast<uint32_t>(int64_val);
    case Type::kUint64:
      return static_cast<uint32_t>(uint64_val);
    case Type::kString:
      break;
  }
  return 0;
}

uint64_t DecodedField::as_uint64() const {
  switch (type) {
    case Type::kUint64:
      return uint64_val;
    case Type::kUint32:
      return uint32_val;
    case Type::kInt64:
      return static_cast<uint64_t>(int64_val);
    case Type::kInt32:
      return static_cast<uint64_t>(int32_val);
    case Type::kString:
      break;
  }
  return 0;
}

base::StringView DecodedField::as_string() const {
  return string_val;
}

// static
int64_t FtraceExtensionParser::AdjustTimestampWithField(
    int64_t base_ts,
    base::StringView offset_field_name,
    const std::vector<DecodedField>& fields) {
  for (const auto& f : fields) {
    if (f.name == offset_field_name) {
      return base_ts + f.as_int64();
    }
  }
  return base_ts;
}

// static
std::vector<uint8_t> FtraceExtensionParser::EncodeAtraceCounterEvent(
    uint32_t pid,
    base::StringView name,
    int64_t value) {
  base::StackString<256> buf("C|%u|%.*s|%" PRId64, pid,
                             static_cast<int>(name.size()), name.data(), value);
  protozero::HeapBuffered<protos::pbzero::FtraceEvent> msg;
  msg->set_pid(pid);
  auto* print = msg->set_print();
  print->set_buf(buf.c_str());
  return msg.SerializeAsArray();
}

// static
std::vector<uint8_t> FtraceExtensionParser::EncodeAtraceBeginEvent(
    uint32_t pid,
    base::StringView name) {
  base::StackString<256> buf("B|%u|%.*s", pid, static_cast<int>(name.size()),
                             name.data());
  protozero::HeapBuffered<protos::pbzero::FtraceEvent> msg;
  msg->set_pid(pid);
  auto* print = msg->set_print();
  print->set_buf(buf.c_str());
  return msg.SerializeAsArray();
}

// static
std::vector<uint8_t> FtraceExtensionParser::EncodeAtraceEndEvent(uint32_t pid) {
  base::StackString<32> buf("E|%u", pid);
  protozero::HeapBuffered<protos::pbzero::FtraceEvent> msg;
  msg->set_pid(pid);
  auto* print = msg->set_print();
  print->set_buf(buf.c_str());
  return msg.SerializeAsArray();
}

}  // namespace ftrace_extensions
}  // namespace perfetto::trace_processor
