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

#ifndef SRC_TRACE_PROCESSOR_IMPORTERS_FTRACE_EXTENSIONS_MY_TRACING_MARK_WRITE_PARSER_H_
#define SRC_TRACE_PROCESSOR_IMPORTERS_FTRACE_EXTENSIONS_MY_TRACING_MARK_WRITE_PARSER_H_

#include <vector>

#include "perfetto/ext/base/string_view.h"
#include "src/trace_processor/importers/ftrace/extensions/ftrace_extension_parser.h"

namespace perfetto::trace_processor::ftrace_extensions {

class MyTracingMarkWriteParser : public FtraceExtensionParser {
 public:
  MyTracingMarkWriteParser() = default;
  ~MyTracingMarkWriteParser() override = default;

  base::StringView GetEventName() const override {
    return "my_tracing_mark_write";
  }

  std::vector<SynthesizedEvent> Parse(const ParserContext& ctx) override;
};

}  // namespace perfetto::trace_processor::ftrace_extensions

#endif  // SRC_TRACE_PROCESSOR_IMPORTERS_FTRACE_EXTENSIONS_MY_TRACING_MARK_WRITE_PARSER_H_
