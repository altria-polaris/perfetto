#!/usr/bin/env python3
# Copyright (C) 2026 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import struct


def encode_varint(value):
  out = b''
  if value < 0:
    # Handle negative values as 64-bit varints
    value = (1 << 64) + value
  while value >= 0x80:
    out += struct.pack('B', (value & 0x7f) | 0x80)
    value >>= 7
  out += struct.pack('B', value & 0x7f)
  return out


def encode_tag(field_id, wire_type):
  return encode_varint((field_id << 3) | wire_type)


def encode_bytes_field(field_id, data):
  return encode_tag(field_id, 2) + encode_varint(len(data)) + data


def encode_string_field(field_id, s):
  return encode_bytes_field(field_id, s.encode('utf-8'))


def encode_varint_field(field_id, value):
  return encode_tag(field_id, 0) + encode_varint(value)


LEGACY_EVENT_ID = 327


def build_legacy_field_string(name, val):
  field = encode_string_field(1, name)
  field += encode_string_field(3, val)
  return field


def build_legacy_field_int(name, val):
  field = encode_string_field(1, name)
  field += encode_varint_field(4, val)
  return field


def build_legacy_field_uint(name, val):
  field = encode_string_field(1, name)
  field += encode_varint_field(5, val)
  return field


def build_legacy_generic_event(name, fields):
  out = encode_string_field(1, name)
  for f_name, f_type, f_val in fields:
    if f_type == 'str':
      field_bytes = build_legacy_field_string(f_name, f_val)
    elif f_type == 'int':
      field_bytes = build_legacy_field_int(f_name, f_val)
    elif f_type == 'uint':
      field_bytes = build_legacy_field_uint(f_name, f_val)
    out += encode_bytes_field(2, field_bytes)
  return out


def build_ftrace_event(ts, pid, event_id, payload_bytes):
  out = encode_varint_field(1, ts)
  out += encode_varint_field(2, pid)
  out += encode_bytes_field(event_id, payload_bytes)
  return out


def build_trace_packet(bundle):
  return encode_bytes_field(1, bundle)


def main():
  packets = []

  # Legacy generic events packet (no descriptor packet needed!)
  bundle = encode_varint_field(1, 0)  # cpu 0

  # Begin slice: type = 'B' (66), name = "my_slice"
  payload_b = build_legacy_generic_event("my_tracing_mark_write",
                                         [("name", "str", "my_slice"),
                                          ("pid", "int", 1001),
                                          ("type", "uint", 66),
                                          ("value", "uint", 0)])
  bundle += encode_bytes_field(
      2, build_ftrace_event(10000000, 1001, LEGACY_EVENT_ID, payload_b))

  # Counter: type = 'C' (67), name = "my_counter", value = -2
  payload_c = build_legacy_generic_event(
      "my_tracing_mark_write", [("name", "str", "my_counter"),
                                ("pid", "int", 1001), ("type", "uint", 67),
                                ("value", "uint", 18446744073709551614)])
  bundle += encode_bytes_field(
      2, build_ftrace_event(20000000, 1001, LEGACY_EVENT_ID, payload_c))

  # End slice: type = 'E' (69)
  payload_e = build_legacy_generic_event("my_tracing_mark_write",
                                         [("name", "str", ""),
                                          ("pid", "int", 1001),
                                          ("type", "uint", 69),
                                          ("value", "uint", 0)])
  bundle += encode_bytes_field(
      2, build_ftrace_event(30000000, 1001, LEGACY_EVENT_ID, payload_e))

  packets.append(encode_bytes_field(1, build_trace_packet(bundle)))

  for p in packets:
    sys.stdout.buffer.write(p)


if __name__ == "__main__":
  main()
