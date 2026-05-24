# Analysis of tracing_mark_write Ftrace Event Parsing Design

## Architecture Overview: Two-Level Handling of ftrace tracing_mark_write

### Level 1: Event Name Routing (Routing based on group name)

When the ftrace tokenizer receives an event, it routes it based on the event name (formatted as `group:event_name`):

| Group | Event Name | Handler |
|---|---|---|
| mdss | mdss:tracing_mark_write | ParseMdssTracingMarkWrite → ParseKernelTracingMarkWrite |
| samsung | samsung_tracing_mark_write | ParseSamsungTracingMarkWrite → ParseKernelTracingMarkWrite |
| mali | mali_tracing_mark_write | ParseMaliTracingMarkWrite → ParseKernelTracingMarkWrite |
| sde | sde_tracing_mark_write | ParseSdeTracingMarkWrite → ParseKernelTracingMarkWrite |
| dpu | dpu_tracing_mark_write | ParseDpuTracingMarkWrite → ParseKernelTracingMarkWrite |
| g2d | g2d_tracing_mark_write | ParseG2dTracingMarkWrite → ParseKernelTracingMarkWrite |
| lwis | lwis_tracing_mark_write | ParseLwisTracingMarkWrite → ParseKernelTracingMarkWrite |
| Unknown Group | No dedicated handler | Falls back to generic print event (field #27) |

### Level 2: Parser of buf format

Each dedicated handler acts similarly, converting the binary protobuf consisting of structured fields (containing `trace_type`, `trace_begin`, `trace_name`, `value`, etc.) into `ParseKernelTracingMarkWrite(timestamp, pid, trace_type, trace_begin, trace_name, tgid, value)`.

Then, `ParseKernelTracingMarkWrite` handles based on `trace_type`:
- 'B' → begin slice
- 'E' → end slice
- 'C' → counter
- 'I' → instant

Regardless of the group, they are eventually converted to atrace phases (B/E/C/I) and passed to the same `ParseSystracePoint` for processing.

---

## Question: What happens to unknown groups?

They will not be parsed automatically; they fall back to `ParsePrint → SystraceParser::ParsePrintEvent(evt.buf())`.

`ParsePrint` simply treats `PrintFtraceEvent.buf` as a raw text string, and passes it to `ParseSystraceTracePoint` to try to parse it in `B|1636|name` format. That is:

1. If the kernel driver of that unknown group happens to write to `buf` in the exact atrace text format (`B|1636|name`, `C|1636|counter_name|123`, etc.), it can be successfully parsed.
2. If the kernel driver writes in any other format, the parsing will fail and the event will be discarded.

Therefore, known groups like mdss/samsung/mali work because the kernel driver already parsed the raw `trace_marker` data into structured fields (`trace_name`, `trace_type`, `trace_begin`), allowing Perfetto's `ParseXxxTracingMarkWrite` to parse them correctly.

Your commit `079e360` added `TokenizeFtraceGgo` to manually handle an unknown group (`ggo`) by decoding its payload, reassembling it into the atrace text format, and pushing it back.