/*
 * Copyright (C) 2025 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed Mirror in the License for the
 * specific language governing permissions and limitations under the License.
 */

#include "src/trace_processor/importers/ftrace/extensions/ftrace_extension_registry.h"

#include "perfetto/protozero/proto_decoder.h"
#include "protos/perfetto/trace/ftrace/ftrace_event.pbzero.h"
#include "src/trace_processor/importers/ftrace/generic_ftrace_tracker.h"
#include "src/trace_processor/types/trace_processor_context.h"

namespace perfetto::trace_processor {
namespace ftrace_extensions {

// static
FtraceExtensionRegistry* FtraceExtensionRegistry::GetOrCreate(
    TraceProcessorContext* ctx) {
  if (!ctx->ftrace_extension_registry) {
    ctx->ftrace_extension_registry = new FtraceExtensionRegistry();
  }
  return static_cast<FtraceExtensionRegistry*>(ctx->ftrace_extension_registry);
}

void FtraceExtensionRegistry::Register(
    std::unique_ptr<FtraceExtensionParser> parser) {
  std::string name = parser->GetEventName().ToStdString();
  parsers_.Insert(name, std::move(parser));
}

FtraceExtensionParser* FtraceExtensionRegistry::Find(
    base::StringView event_name) {
  auto* p = parsers_.Find(event_name.ToStdString());
  return p ? p->get() : nullptr;
}

// static
bool FtraceExtensionRegistry::DecodeFields(
    const TraceBlobView& event,
    TraceProcessorContext* context,
    GenericFtraceTracker* generic_tracker,
    std::vector<DecodedField>* out_fields,
    StringId* out_event_name) {
  protozero::ProtoDecoder ftrace_decoder(event.data(), event.length());

  // 1. Find the event ID from FtraceEvent header
  uint32_t event_id = 0;
  for (auto fld = ftrace_decoder.ReadField(); fld.valid();
       fld = ftrace_decoder.ReadField()) {
    if (fld.id() != protos::pbzero::FtraceEvent::kTimestampFieldNumber &&
        fld.id() != protos::pbzero::FtraceEvent::kPidFieldNumber) {
      event_id = fld.id();
      break;
    }
  }
  if (event_id == 0)
    return false;

  // 2. Get the descriptor from GenericFtraceTracker
  auto* descriptor = generic_tracker->GetEvent(event_id);
  if (!descriptor)
    return false;

  *out_event_name = descriptor->name;

  // 3. Decode the sub-message payload using the descriptor
  auto payload_fld = ftrace_decoder.FindField(event_id);
  if (!payload_fld)
    return false;

  protozero::ProtoDecoder payload_decoder(payload_fld.data(),
                                          payload_fld.size());
  for (auto fld = payload_decoder.ReadField(); fld.valid();
       fld = payload_decoder.ReadField()) {
    if (fld.id() >= descriptor->fields.size())
      continue;

    auto& field_desc = descriptor->fields[fld.id()];
    DecodedField df;
    df.field_id = fld.id();
    df.name = context->storage->GetString(field_desc.name);

    using ProtoSchemaType = protozero::proto_utils::ProtoSchemaType;
    if (field_desc.type == ProtoSchemaType::kInt64) {
      df.type = DecodedField::Type::kInt64;
      df.int64_val = fld.as_int64();
    } else if (field_desc.type == ProtoSchemaType::kInt32) {
      df.type = DecodedField::Type::kInt32;
      df.int32_val = fld.as_int32();
    } else if (field_desc.type == ProtoSchemaType::kUint32) {
      df.type = DecodedField::Type::kUint32;
      df.uint32_val = fld.as_uint32();
    } else if (field_desc.type == ProtoSchemaType::kUint64) {
      df.type = DecodedField::Type::kUint64;
      df.uint64_val = fld.as_uint64();
    } else if (field_desc.type == ProtoSchemaType::kString) {
      df.type = DecodedField::Type::kString;
      df.string_val = base::StringView(
          reinterpret_cast<const char*>(fld.data()), fld.size());
    } else {
      continue;
    }

    out_fields->push_back(df);
  }

  return true;
}

}  // namespace ftrace_extensions
}  // namespace perfetto::trace_processor
