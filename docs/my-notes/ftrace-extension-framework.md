# Ftrace Extension Framework Development Documentation

## Overview

This system (Ftrace Extension Framework) is used to extensibly handle unknown Generic Ftrace Events in Perfetto TraceProcessor.

When encountering events named `example` (or the original `ggo`), their Field IDs can change across different Android versions, causing traditional static Field ID queries to fail. This framework matches events by **Event Name (String)** and decodes payloads using dynamic descriptors provided by `GenericFtraceTracker`, ensuring cross-device compatibility.

## System Architecture

The data flow is as follows:

```
FtraceTokenizer
    └── TryTokenizeUnknownGroupEvent()
            ├── FtraceExtensionRegistry::DecodeFields()  // Decode using dynamic descriptors
            ├── Registry->Find(event_name)                // Search parser by event name string
            └── parser->Parse(ctx)                       // Run custom parsing logic
                    └── Generate SynthesizedEvent (atrace format) pushed to Sorter
```

## Directory Structure

```
src/trace_processor/importers/ftrace/extensions/
├── ftrace_extension_parser.h    # Abstract base class and basic structs
├── ftrace_extension_parser.cc  # Core helper implementations (e.g. EncodeAtrace)
├── ftrace_extension_registry.h # Parser registry center
├── ftrace_extension_registry.cc
├── example_aggregated_event.h  # Example implementation (Aggregation -> Decomposition)
├── example_aggregated_event.cc
└── BUILD.gn
```

## Core Design Decisions

1. **Event Name Matching**: Completely independent of static Field IDs, adapting to dynamically defined ftrace events.
2. **Plugin Registration**: Manage all custom parsers via `FtraceExtensionRegistry` to achieve high decoupling.
3. **Dynamic Decoding (DecodeFields)**: Registry invokes descriptor information from `GenericFtraceTracker` to convert binary data into a list of `DecodedField`s. Parsers only focus on field names.
4. **Synthesized Events (SynthesizedEvent)**: Parsers can convert one input event into zero or more synthesized events (e.g., decomposing aggregated events). These are formatted as `atrace` and pushed back to the Sorter for sorting and visualization.
5. **Strict Compilation Compatibility**: Internal implementation uses an `if-else` chain instead of `switch` for Proto types, avoiding `-Wswitch-enum` warnings and ensuring stable compilation in the Perfetto core library.

## Core Class Descriptions

### FtraceExtensionParser (Base)
The base class for all custom parsers. It provides static helper functions like `EncodeAtraceCounterEvent` to easily generate standard atrace events.

### ParserContext
The context passed to `Parse()`, containing:
* `decoded_fields`: List of decoded fields (including names, types, and values).
* `pid`: Process ID where the event occurred.
* `cpu`: CPU core where the event occurred.

### FtraceExtensionRegistry
Singleton pattern. Created during `FtraceModuleImpl` initialization and holds all registered parser instances.

## Development Workflow

1. **Define Parser**: Inherit from `FtraceExtensionParser`.
2. **Register Parser**: Register in `ftrace_module_impl.cc`.
3. **Compile**: Compile using `tools/ninja -C out/linux trace_processor_shell`.
4. **Verify**: Generate test traces using `tools/gen_example_trace.py` and inspect them using the UI or shell.

## Considerations
* **Memory Management**: The Registry holds the `std::unique_ptr` of the parsers, and its lifecycle aligns with `TraceProcessorContext`.
* **Performance**: Lookups use `FlatHashMap` with O(1) complexity; the decoding process is optimized to minimize unnecessary copies.
