# Perfetto TraceProcessor Development Memo

## Useful Commands

### Check Output Directory
```bash
echo $OUT                              # Use this if set
ls -t1 out | head -n1                  # Otherwise, find the latest
```

### Compile
```bash
# Generate GN config (required after modifying .gn/.gni files)
tools/gn gen --check out/linux

# Compile (use $OUT instead of directly inlining command)
tools/ninja -C $OUT trace_processor_shell

# Fix GN dependencies
tools/gn check out/linux
```

### Test
```bash
# Unit Tests
out/linux/perfetto_unittests --gtest_brief=1 --gtest_filter="TestSuite.*"

# Diff Tests
tools/diff_test_trace_processor.py out/linux/trace_processor_shell --name-filter="TestName"
```

### Format and Presubmit Checks
Before committing or pushing, verify code style and formatting to prevent git hook failures:
```bash
# Automatically format all modified sources (C++, Python, GN, SQL, Rust, etc.)
tools/format-sources

# Run the complete local presubmit suite (checks formats, compiles, tests)
tools/run_presubmit
```

### Commit
```bash
# View current modifications
git status
git diff $(git config branch.$(git rev-parse --abbrev-ref HEAD).parent)

# Commit changes (separate commits for distinct features)
git add -A
git commit -m "tp: [description of change]

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Project Architecture

```
src/trace_processor/
├── importers/
│   ├── ftrace/           # ftrace event parsing
│   │   ├── ftrace_tokenizer.cc      # Entry point
│   │   ├── generic_ftrace_tracker.cc # Dynamic descriptor tracker
│   │   └── extensions/              # Extensibility mechanism (parsers & registry)
│   ├── proto/            # protobuf parsing
│   └── syscalls/         # syscall handling
├── storage/              # trace storage (sqlite)
└── types/                # Shared types
```

## Ftrace Extension Mechanism

Used to handle generic ftrace events (like `example` or the original `ggo`) where the field IDs change across different Android versions but the event name remains constant.

See:
- [ftrace-extension-framework.md](./ftrace-extension-framework.md) (架構與設計說明)
- [execution-workflow.md](./execution-workflow.md) (執行步驟、問題解決與自訂事件用途整理)
- [legacy-generic-ftrace-investigation.md](./legacy-generic-ftrace-investigation.md) (Android 16 舊版本 Generic Ftrace Extension 解析失敗調查與解決方案)

## Common Issues & Troubleshooting

### 1. use of undeclared identifier
Missing `#include` statements. Check if you need a full definition instead of a forward declaration.

### 2. incomplete type
You need to `#include` the full header file; a forward declaration is not sufficient.

### 3. no newline at end of file
GCC/Clang's `-Wnewline-eof` treats this as an error. Add a newline at the end of the file (e.g. `printf '\n' >> file`).

### 4. call to deleted constructor
`TraceBlobView` is not copyable and can only be passed by reference (e.g., `const TraceBlobView&`).

### 5. ProtoSchemaType vs ProtoWireType
`inner.type()` returns the wire type, whereas you should compare against `field_desc.type` (schema type).

### 6. enumeration values not explicitly handled in switch
`-Werror,-Wswitch-enum` requires all enum values to have explicit cases in a `switch`. Avoid this by using `default:` or an `if-else` chain:
```cpp
case Type::kKnownValue:
  // ...
  break;
case Type::kOtherValue:
default:
  continue;  // Or other appropriate fallback
```

## Contacts & Resources

- Original Development Context: Conversations with Altria (May 2026)
- Testing: Requires verification using `trace_processor_shell` and SQL queries
- Reference: `GenericFtraceTracker` (handles unknown generic event descriptors)