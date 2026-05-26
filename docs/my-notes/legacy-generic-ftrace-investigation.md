# Android 16 與舊版本 Generic Ftrace Extension 解析失敗調查與解決方案

本文件詳細記錄了自訂 Ftrace 擴充解析器（以 `my_tracing_mark_write` 為例）在 Android 16（或更早版本）上無法正常解析的調查過程、問題根源以及對應的解決方案。

---

## 1. 問題描述
我們實作了一個自訂的 `tracing_mark_write` 擴充解析器（[MyTracingMarkWriteParser](file:///home/altria/my-perfetto/src/trace_processor/importers/ftrace/extensions/my_tracing_mark_write_parser.h)），用於解析與轉譯特殊的 64 位元 GPU/硬體計數器事件。
* **現象**：在最新版的 Android 上此解析器運作正常，但在 Android 16（或更舊版本）的裝置上收集的 Trace 中，該解析器未被呼叫，事件被當作常規 Ftrace 事件寫入 `raw` 表，未能生成對應的 `slice` 與 `counter` 事件。

---

## 2. 調查過程與問題分析

為了定位問題，我們深入分析了 Perfetto 的 `TraceProcessor` 原始碼，追蹤 Ftrace 事件從**分詞（Tokenization）**到**解析（Parsing）**的流程：

### A. Ftrace 序列化格式的歷史演進 (Generic Ftrace Events)
在 Perfetto 中，通用 Ftrace 事件（意即在編譯期不存在專屬 Protobuf Schema 的事件，需動態依據 `/format` 檔案解析）有兩種序列化與編碼方式：

1. **新版動態編碼 (`denser_generic_event_encoding`)** —— **Perfetto v50+ 引入（v53.0 起預設啟用）**：
   - 每個通用事件會被編碼為 `FtraceEvent` proto 中的一個動態子訊息，其欄位 ID $\ge 65536$。
   - Trace 的 `FtraceEventBundle` 中會附帶一個 `GenericEventDescriptor`，告知欄位 ID 與動態生成的 Protobuf 描述符的映射關係。
2. **舊版/Legacy 通用編碼** —— **Android 16（或更早版本）或未啟用 denser 模式**：
   - 所有通用事件會被統一封裝在 `FtraceEvent` 的第 `327` 號欄位中，其訊息類型為 [GenericFtraceEvent](file:///home/altria/my-perfetto/protos/perfetto/trace/ftrace/generic.proto#L23-L35)：
     ```protobuf
     message GenericFtraceEvent {
       message Field {
         optional string name = 1;
         oneof value {
           string str_value = 3;
           int64 int_value = 4;
           uint64 uint_value = 5;
         }
       }
       optional string event_name = 1;
       repeated Field field = 2;
     }
     ```

---

### B. 追蹤 Tokenizer 的處理分流
在 [ftrace_tokenizer.cc](file:///home/altria/my-perfetto/src/trace_processor/importers/ftrace/ftrace_tokenizer.cc) 中，`TokenizeFtraceEvent` 負責識別事件 ID 並進行分流：

```cpp
// 原始程式碼：
if (GenericFtraceTracker::IsGenericFtraceEvent(
        static_cast<uint32_t>(event_id))) {
  if (TryTokenizeUnknownGroupEvent(cpu, *timestamp, event, state)) {
    return;
  }
}
```

其中 `GenericFtraceTracker::IsGenericFtraceEvent` 的實作定義於 [generic_ftrace_tracker.h](file:///home/altria/my-perfetto/src/trace_processor/importers/ftrace/generic_ftrace_tracker.h#L75-L77)：
```cpp
static bool IsGenericFtraceEvent(uint32_t pb_field_id) {
  return pb_field_id >= kGenericEvtProtoMinPbFieldId; // kGenericEvtProtoMinPbFieldId = 65536
}
```

#### **問題根源 1**
在 Android 16 或舊版本產生的 Trace 中，`event_id` 為 `327`（`FtraceEvent::kGenericFieldNumber`）。
* 因為 `327 < 65536`，`IsGenericFtraceEvent` 回傳 `false`。
* 這導致舊版的通用事件**完全繞過了 `TryTokenizeUnknownGroupEvent`**，無法進入自訂的 Extension Parser 處理流程。

---

### C. 追蹤 Extension 欄位解碼器
即使我們強制將欄位 327 送入 `TryTokenizeUnknownGroupEvent`，它隨後會呼叫 `FtraceExtensionRegistry::DecodeFields`：

```cpp
// 原始程式碼：
bool FtraceExtensionRegistry::DecodeFields(
    const TraceBlobView& event,
    TraceProcessorContext* context,
    GenericFtraceTracker* generic_tracker,
    std::vector<DecodedField>* out_fields,
    StringId* out_event_name) {
  protozero::ProtoDecoder ftrace_decoder(event.data(), event.length());
  ...
  // 獲取 Generic Ftrace Tracker 中的動態 Descriptor
  auto* descriptor = generic_tracker->GetEvent(event_id);
  if (!descriptor)
    return false; // 對於 327，由於沒有透過 bundle 註冊動態 Descriptor，此處會回傳 false 失敗
```

#### **問題根源 2**
`DecodeFields` 的原始設計僅預期解碼新版動態描述符事件。當接收到 Legacy 的 `GenericFtraceEvent` (ID 327) 時，因找不到對應的動態描述符，解碼流程會直接中斷並回傳 `false`。

---

## 3. 解決方案實作

為了同時相容 Android 16（或更舊）的舊版 Legacy Generic Event，我們做出了兩處修改：

### 修改一：擴充 Tokenizer 分流條件
在 [ftrace_tokenizer.cc](file:///home/altria/my-perfetto/src/trace_processor/importers/ftrace/ftrace_tokenizer.cc) 中，將 `FtraceEvent::kGenericFieldNumber` (327) 納入 Extension 解析流程的觸發條件：

```diff
   if (GenericFtraceTracker::IsGenericFtraceEvent(
-          static_cast<uint32_t>(event_id))) {
+          static_cast<uint32_t>(event_id)) ||
+      event_id == protos::pbzero::FtraceEvent::kGenericFieldNumber) {
     if (TryTokenizeUnknownGroupEvent(cpu, *timestamp, event, state)) {
       return;
     }
   }
```

### 修改二：在 Registry 中實作 Legacy 欄位解碼
在 [ftrace_extension_registry.cc](file:///home/altria/my-perfetto/src/trace_processor/importers/ftrace/extensions/ftrace_extension_registry.cc) 中，當檢測到 `event_id == FtraceEvent::kGenericFieldNumber` 時，改用舊版的 `GenericFtraceEvent::Decoder` 進行解碼，並填入 `DecodedField` 結構體中：

```cpp
  if (event_id == protos::pbzero::FtraceEvent::kGenericFieldNumber) {
    auto payload_fld = ftrace_decoder.FindField(event_id);
    if (!payload_fld)
      return false;

    protos::pbzero::GenericFtraceEvent::Decoder gen_decoder(payload_fld.data(),
                                                            payload_fld.size());
    *out_event_name = context->storage->InternString(gen_decoder.event_name());

    uint32_t next_field_id = 1;
    for (auto it = gen_decoder.field(); it; ++it) {
      protos::pbzero::GenericFtraceEvent::Field::Decoder fld(*it);
      DecodedField df;
      df.field_id = next_field_id++;
      df.name = context->storage->GetString(context->storage->InternString(fld.name()));
      if (fld.has_int_value()) {
        df.type = DecodedField::Type::kInt64;
        df.int64_val = fld.int_value();
      } else if (fld.has_uint_value()) {
        df.type = DecodedField::Type::kUint64;
        df.uint64_val = fld.uint_value();
      } else if (fld.has_str_value()) {
        df.type = DecodedField::Type::kString;
        auto str = fld.str_value();
        df.string_val = base::StringView(str.data, str.size);
      } else {
        continue;
      }
      out_fields->push_back(df);
    }
    return true;
  }
```

---

## 4. 驗證結果

1. **測試案例**：我們實作了 [my_legacy_tracing_mark_write_test.py](file:///home/altria/my-perfetto/test/trace_processor/diff_tests/parser/ftrace/my_legacy_tracing_mark_write_test.py)，用以模擬產生舊版編碼格式（ID 327）的二進位 Trace。
2. **測試指令**：
   ```bash
   .venv/bin/python3 tools/diff_test_trace_processor.py out/linux/trace_processor_shell --name-filter=".*my_legacy_tracing_mark_write.*"
   ```
3. **驗證結果**：測試順利通過！說明在面臨舊版本的 Ftrace 通用事件時，自訂 Extension Parser 已經可以正確執行，並完美地將舊版編碼解析為我們期望的 Slice 或 Counter。
   ```text
   [==========] Running 1 tests.
   [==========] Name filter selected 1 tests out of 1365.
   [==========] 1 tests ran out of 1 total. (245 ms total)
   [  PASSED  ] 1 tests.
   ```
