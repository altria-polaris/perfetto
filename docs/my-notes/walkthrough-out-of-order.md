# Walkthrough: Complex Out-of-Order Trace Test

We have successfully updated the out-of-order trace generator and verification query to simulate a complex, realistic Android App stopwatch flow, interspersed with two groups of non-monotonic, out-of-order counter events.

## Changes Implemented

### 1. Updated Trace Generator Script
File: [gen_ooo_trace.py](file:///home/altria/perfetto/tools/gen_ooo_trace.py)

- **Process Tree Mapping**: Added process metadata mapping TID 1000 (`StopwatchUI`) and TID 1001 (`RenderThread`) to PID 1000 (`com.example.stopwatch`).
- **Periodic Frame Loop (1s to 35s)**:
  - **UI Thread**: `Choreographer#doFrame` -> `StopwatchApp::onTimerTick` -> `draw`
  - **RenderThread**: `DrawFrame` -> `vkQueueSubmit` -> `vkQueuePresentKHR`
- **Group 1 Out-of-Order Events**:
  - Injected after 15s with `base_ts = 15s`.
  - Configured with non-monotonic offsets `[2.8s, 6.9s, 0.95s, 4.7s, 7.6s, 1.85s, 5.75s, 3.9s]`.
  - Synthesized timestamps fall non-monotonically in the range of 7.4s to 14.05s.
- **Group 2 Out-of-Order Events**:
  - Injected after 30s with `base_ts = 30s`.
  - Configured with non-monotonic offsets `[3.8s, 7.9s, 1.95s, 5.7s, 0.6s, 4.75s, 6.75s, 2.9s]`.
  - Synthesized timestamps fall non-monotonically in the range of 22.1s to 29.4s.

### 2. Created and Updated SQL Verification Queries
- **Interspersed Timeline Verification**: [test_query_ooo.sql](file:///home/altria/perfetto/test_query_ooo.sql)
- **Counter Sorting Verification**: [test_query_ooo_counters.sql](file:///home/altria/perfetto/test_query_ooo_counters.sql)

---

## Verification Results

### 1. Counter Sorting Verification
Running the query to view `ooo_counter_*` values ordered by row insertion ID (`counter.id ASC`):
```bash
out/android/trace_processor_shell -q test_query_ooo_counters.sql test_ooo.perfetto-trace
```

Output:
```csv
"id","ts","name","value"
0,7400000000,"ooo_counter_5",500.000000
1,8100000000,"ooo_counter_2",200.000000
2,9250000000,"ooo_counter_7",700.000000
3,10300000000,"ooo_counter_4",400.000000
4,11100000000,"ooo_counter_8",800.000000
5,12200000000,"ooo_counter_1",100.000000
6,13150000000,"ooo_counter_6",600.000000
7,14050000000,"ooo_counter_3",300.000000
8,22100000000,"ooo_counter_2",2000.000000
9,23250000000,"ooo_counter_7",7000.000000
10,24300000000,"ooo_counter_4",4000.000000
11,25250000000,"ooo_counter_6",6000.000000
12,26200000000,"ooo_counter_1",1000.000000
13,27100000000,"ooo_counter_8",8000.000000
14,28050000000,"ooo_counter_3",3000.000000
15,29400000000,"ooo_counter_5",5000.000000
```
> [!NOTE]
> All counter row IDs strictly increment monotonically with `ts` increasing from `7.4s` to `29.4s`, proving that the non-monotonic offsets were successfully parsed and chronologically sorted by the trace sorter prior to storage insertion.

### 2. Slices and Counters Interleaved Timeline
Running the query to verify that out-of-order counter events are successfully interspersed with frame-drawing events:
```bash
out/android/trace_processor_shell -q test_query_ooo.sql test_ooo.perfetto-trace
```

Truncated timeline snippet (around 22s - 23s range):
```csv
"slice",22000000000,"StopwatchUI","Choreographer#doFrame"
"slice",22001000000,"StopwatchUI","StopwatchApp::onTimerTick"
"slice",22006000000,"StopwatchUI","draw"
"slice",22010000000,"[NULL]","DrawFrame"
"slice",22011000000,"[NULL]","vkQueueSubmit"
"slice",22019000000,"[NULL]","vkQueuePresentKHR"
"counter",22100000000,"ooo_counter_2","value: 2000.0"
"slice",23000000000,"StopwatchUI","Choreographer#doFrame"
"slice",23001000000,"StopwatchUI","StopwatchApp::onTimerTick"
"slice",23006000000,"StopwatchUI","draw"
"slice",23010000000,"[NULL]","DrawFrame"
"slice",23011000000,"[NULL]","vkQueueSubmit"
"slice",23019000000,"[NULL]","vkQueuePresentKHR"
"counter",23250000000,"ooo_counter_7","value: 7000.0"
```
> [!NOTE]
> Slices are correctly associated with the `StopwatchUI` thread name. The out-of-order counter events are perfectly interspersed (e.g. counter 2 with value 2000 at `22.1s` and counter 7 with value 7000 at `23.25s`) chronologically in between the frame events.
