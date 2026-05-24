#!/usr/bin/env python3
# Copyright (C) 2025 The Android Open Source Project
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

import os
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


EVENT_B_ID = 80001
EVENT_A_ID = 80002


def build_event_b_descriptor():
  fields = [(1, "base_ts", 3)]  # 3 is TYPE_INT64
  inner = encode_string_field(1, "event_b")
  for fid, name, type_id in fields:
    field_desc = encode_string_field(1, name)
    field_desc += encode_varint_field(3, fid)
    field_desc += encode_varint_field(5, type_id)
    inner += encode_bytes_field(2, field_desc)
  return inner


def build_event_a_descriptor():
  fields = []
  for i in range(1, 9):
    fields.append((i * 3 - 2, f"off{i}", 3))  # TYPE_INT64
    fields.append((i * 3 - 1, f"val{i}", 5))  # TYPE_INT32
    fields.append((i * 3, f"name{i}", 9))  # TYPE_STRING
  inner = encode_string_field(1, "event_a")
  for fid, name, type_id in fields:
    field_desc = encode_string_field(1, name)
    field_desc += encode_varint_field(3, fid)
    field_desc += encode_varint_field(5, type_id)
    inner += encode_bytes_field(2, field_desc)
  return inner


def build_event_b_payload(base_ts):
  return encode_varint_field(1, base_ts)


def build_event_a_payload(offsets, values, names):
  out = b''
  for i in range(1, 9):
    out += encode_varint_field(i * 3 - 2, offsets[i - 1])
    out += encode_varint_field(i * 3 - 1, values[i - 1])
    out += encode_string_field(i * 3, names[i - 1])
  return out


def build_ftrace_event(ts, pid, event_id, payload_bytes):
  out = encode_varint_field(1, ts)
  out += encode_varint_field(2, pid)
  out += encode_bytes_field(event_id, payload_bytes)
  return out


def build_trace_packet(bundle):
  return encode_bytes_field(1, bundle)


def main():
  pid = 1234
  packets = []

  # 1. Descriptor Packet for B
  entry_b = encode_varint_field(1, EVENT_B_ID)
  entry_b += encode_bytes_field(2, build_event_b_descriptor())
  bundle_b_desc = encode_varint_field(1, 0)  # cpu 0
  bundle_b_desc += encode_bytes_field(11, entry_b)
  packets.append(encode_bytes_field(1, build_trace_packet(bundle_b_desc)))

  # 2. Descriptor Packet for A
  entry_a = encode_varint_field(1, EVENT_A_ID)
  entry_a += encode_bytes_field(2, build_event_a_descriptor())
  bundle_a_desc = encode_varint_field(1, 0)
  bundle_a_desc += encode_bytes_field(11, entry_a)
  packets.append(encode_bytes_field(1, build_trace_packet(bundle_a_desc)))

  # 3. Event B (Base Timestamp Event)
  # The packet arrives at 10s (10,000,000,000 ns).
  # The payload tells us the base_ts is 10s.
  base_ts = 10_000_000_000
  bundle = encode_varint_field(1, 0)
  payload_b = build_event_b_payload(base_ts)
  # Packet FtraceEvent header ts = 10s
  bundle += encode_bytes_field(
      2, build_ftrace_event(base_ts, pid, EVENT_B_ID, payload_b))
  packets.append(encode_bytes_field(1, build_trace_packet(bundle)))

  # 4. Event A (Decomposed Events out-of-order)
  # The packet arrives at 15s (15,000,000,000 ns).
  # Its payload has offsets from 1s to 8s.
  # Synthesized timestamps will be 9s, 8s, 7s... 2s.
  # Since these are BEFORE the FtraceEvent header ts (15s) and base_ts (10s),
  # they are generated out of order.
  offsets = [1_000_000_000 * i for i in range(1, 9)]  # 1s, 2s, 3s.. 8s
  values = [100 * i for i in range(1, 9)]  # 100, 200.. 800
  names = [f"ooo_counter_{i}" for i in range(1, 9)]

  bundle = encode_varint_field(1, 0)
  payload_a = build_event_a_payload(offsets, values, names)
  # Packet FtraceEvent header ts = 15s
  bundle += encode_bytes_field(
      2, build_ftrace_event(15_000_000_000, pid, EVENT_A_ID, payload_a))
  packets.append(encode_bytes_field(1, build_trace_packet(bundle)))

  with open("test_ooo.perfetto-trace", "wb") as f:
    for p in packets:
      f.write(p)

  print("Generated test_ooo.perfetto-trace")


if __name__ == "__main__":
  main()
