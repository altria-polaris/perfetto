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

#ifndef SRC_TRACE_PROCESSOR_IMPORTERS_FTRACE_EXTENSIONS_FTRACE_EXTENSION_REGISTRY_H_
#define SRC_TRACE_PROCESSOR_IMPORTERS_FTRACE_EXTENSIONS_FTRACE_EXTENSION_REGISTRY_H_

#include <vector>

#include "perfetto/ext/base/flat_hash_map.h"
#include "perfetto/ext/base/string_view.h"
#include "perfetto/trace_processor/trace_blob_view.h"
#include "src/trace_processor/importers/ftrace/extensions/ftrace_extension_parser.h"

namespace perfetto::trace_processor {

class TraceProcessorContext;
class GenericFtraceTracker;

namespace ftrace_extensions {

// Singleton registry for custom ftrace event parsers.
class FtraceExtensionRegistry {
 public:
  static FtraceExtensionRegistry* GetOrCreate(TraceProcessorContext* ctx);

  void Register(std::unique_ptr<FtraceExtensionParser> parser);

  FtraceExtensionParser* Find(base::StringView event_name);

  // Decodes the proto payload of a generic ftrace event into DecodedField.
  static bool DecodeFields(const TraceBlobView& event,
                           TraceProcessorContext* context,
                           GenericFtraceTracker* generic_tracker,
                           std::vector<DecodedField>* out_fields,
                           StringId* out_event_name);

 private:
  FtraceExtensionRegistry() = default;

  base::FlatHashMap<std::string, std::unique_ptr<FtraceExtensionParser>>
      parsers_;
};

}  // namespace ftrace_extensions
}  // namespace perfetto::trace_processor

#endif  // SRC_TRACE_PROCESSOR_IMPORTERS_FTRACE_EXTENSIONS_FTRACE_EXTENSION_REGISTRY_H_
