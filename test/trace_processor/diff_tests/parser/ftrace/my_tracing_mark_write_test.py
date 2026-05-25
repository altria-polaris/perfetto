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


EVENT_ID = 80003


def build_my_tracing_mark_write_descriptor():
  # Fields:
  # name: string (field 1, TYPE_STRING = 9)
  # pid: int32 (field 2, TYPE_INT32 = 5)
  # type: uint32 (field 3, TYPE_UINT32 = 13)
  # value: uint64 (field 4, TYPE_UINT64 = 4)
  fields = [(1, "name", 9), (2, "pid", 5), (3, "type", 13), (4, "value", 4)]
  inner = encode_string_field(1, "my_tracing_mark_write")
  for fid, name, type_id in fields:
    field_desc = encode_string_field(1, name)
    field_desc += encode_varint_field(3, fid)
    field_desc += encode_varint_field(5, type_id)
    inner += encode_bytes_field(2, field_desc)
  return inner


def build_my_tracing_mark_write_payload(name, pid, event_type, value):
  out = b''
  out += encode_string_field(1, name)
  out += encode_varint_field(2, pid)
  out += encode_varint_field(3, event_type)
  out += encode_varint_field(4, value)
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

  # 1. Descriptor Packet
  entry = encode_varint_field(1, EVENT_ID)
  entry += encode_bytes_field(2, build_my_tracing_mark_write_descriptor())
  bundle_desc = encode_varint_field(1, 0)  # cpu 0
  bundle_desc += encode_bytes_field(11, entry)
  packets.append(encode_bytes_field(1, build_trace_packet(bundle_desc)))

  # 2. Events Packet
  bundle = encode_varint_field(1, 0)  # cpu 0

  # Begin slice: type = 'B' (66), name = "my_slice"
  payload_b = build_my_tracing_mark_write_payload("my_slice", 1001, 66, 0)
  bundle += encode_bytes_field(
      2, build_ftrace_event(10000000, 1001, EVENT_ID, payload_b))

  # Counter: type = 'C' (67), name = "my_counter", value = 18446744073709551614
  payload_c = build_my_tracing_mark_write_payload("my_counter", 1001, 67,
                                                  18446744073709551614)
  bundle += encode_bytes_field(
      2, build_ftrace_event(20000000, 1001, EVENT_ID, payload_c))

  # End slice: type = 'E' (69)
  payload_e = build_my_tracing_mark_write_payload("", 1001, 69, 0)
  bundle += encode_bytes_field(
      2, build_ftrace_event(30000000, 1001, EVENT_ID, payload_e))

  packets.append(encode_bytes_field(1, build_trace_packet(bundle)))

  for p in packets:
    sys.stdout.buffer.write(p)


if __name__ == "__main__":
  main()
