# How to Add a Custom Ftrace Event Parser

This document explains how to add a custom ftrace event parser using the `FtraceExtensionParser` framework.

## Step 1: Create the Parser Class

Create new `.h` and `.cc` files under the `src/trace_processor/importers/ftrace/extensions/` directory.

### Example Header (`my_event_parser.h`)
```cpp
#include "src/trace_processor/importers/ftrace/extensions/ftrace_extension_parser.h"

namespace perfetto::trace_processor::ftrace_extensions {

class MyEventParser : public FtraceExtensionParser {
 public:
  base::StringView GetEventName() const override { return "my_custom_event"; }
  std::vector<SynthesizedEvent> Parse(const ParserContext& ctx) override;
};

}
```

### Example Implementation (`my_event_parser.cc`)
```cpp
#include "src/trace_processor/importers/ftrace/extensions/my_event_parser.h"
#include "perfetto/ext/base/string_utils.h"

namespace perfetto::trace_processor::ftrace_extensions {

std::vector<SynthesizedEvent> MyEventParser::Parse(const ParserContext& ctx) {
  std::vector<SynthesizedEvent> results;
  
  // Access field values via ctx.decoded_fields
  for (const auto& field : ctx.decoded_fields) {
    if (field.name == "my_val") {
       // Generate a synthesized event
       SynthesizedEvent ev;
       ev.timestamp_ns = ...; 
       ev.ftrace_event_bytes = EncodeAtraceCounterEvent(ctx.pid, "MyCounter", field.as_int32());
       results.push_back(std::move(ev));
    }
  }
  return results;
}

}
```

## Step 2: Register the Parser

Register it in the constructor of `FtraceModuleImpl` under `src/trace_processor/importers/ftrace/ftrace_module_impl.cc`.

```cpp
#include "src/trace_processor/importers/ftrace/extensions/my_event_parser.h"

FtraceModuleImpl::FtraceModuleImpl(...) {
  // ... other code ...
  auto* registry = ftrace_extensions::FtraceExtensionRegistry::GetOrCreate(context);
  registry->Register(std::make_unique<ftrace_extensions::MyEventParser>());
}
```

## Step 3: Update BUILD.gn

Add the new files to the `sources` list in `src/trace_processor/importers/ftrace/extensions/BUILD.gn`.

## Step 4: Compile and Verify

```bash
tools/ninja -C out/linux trace_processor_shell
```

Use `trace_processor_shell` to read a trace containing the event and check the output.
