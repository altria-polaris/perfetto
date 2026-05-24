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


# Simple manual protobuf encoding helpers
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


def build_example_descriptor():
  # Build a serialised DescriptorProto for the 'example' event
  fields = [
      (1, "base_timestamp", 3),  # kInt64
      (2, "ts1", 3),
      (3, "ts2", 3),
      (4, "ts3", 3),
      (5, "ts4", 3),
      (6, "val1", 5),
      (7, "val2", 5),
      (8, "val3", 5),
      (9, "val4", 5),  # kInt32
  ]

  inner = encode_string_field(1, "example")  # name
  for fid, name, type_id in fields:
    field_desc = encode_string_field(1, name)
    field_desc += encode_varint_field(3, fid)  # number
    field_desc += encode_varint_field(5, type_id)  # type (3=int64, 5=int32)
    inner += encode_bytes_field(2, field_desc)
  return inner


EXAMPLE_FIELD_ID = 80000


def build_example_payload():
  # base_ts = 2s, offsets = 10ms, 20ms, 30ms, 40ms
  out = encode_varint_field(1, 2000000000)  # base
  out += encode_varint_field(2, 10000000)  # ts1
  out += encode_varint_field(3, 20000000)  # ts2
  out += encode_varint_field(4, 30000000)  # ts3
  out += encode_varint_field(5, 40000000)  # ts4
  out += encode_varint_field(6, 100)  # val1
  out += encode_varint_field(7, 200)  # val2
  out += encode_varint_field(8, 300)  # val3
  out += encode_varint_field(9, 400)  # val4
  return out


def build_ftrace_event(ts, pid, payload_bytes=None, print_msg=None):
  out = encode_varint_field(1, ts)
  out += encode_varint_field(2, pid)
  if payload_bytes:
    out += encode_bytes_field(EXAMPLE_FIELD_ID, payload_bytes)
  if print_msg:
    print_field = encode_string_field(2, print_msg)  # buf
    out += encode_bytes_field(3, print_field)  # print field
  return out


def build_trace_packet(bundle):
  # TracePacket: FtraceEventBundle ftrace_events = 1
  return encode_bytes_field(1, bundle)


def main():
  pid = 1234
  packets = []

  # 1. Descriptor Packet
  desc = build_example_descriptor()
  entry = encode_varint_field(1, EXAMPLE_FIELD_ID)
  entry += encode_bytes_field(2, desc)
  bundle = encode_varint_field(1, 0)  # cpu 0
  bundle += encode_bytes_field(11,
                               entry)  # generic_event_descriptors (field 11)
  packets.append(encode_bytes_field(
      1, build_trace_packet(bundle)))  # Trace = repeated TracePacket packet = 1

  # 2. Stopwatch Simulation (Atrace events)
  bundle = encode_varint_field(1, 0)
  bundle += encode_bytes_field(
      2, build_ftrace_event(1000000000, pid, print_msg="B|1234|StopwatchApp"))

  # 10 Counters over 1 second
  for i in range(11):
    ts = 1000000000 + (i * 100000000)  # Every 100ms
    msg = f"C|1234|TimerValue|{i}"
    bundle += encode_bytes_field(2, build_ftrace_event(ts, pid, print_msg=msg))

  bundle += encode_bytes_field(
      2, build_ftrace_event(2100000000, pid, print_msg="E|1234"))
  packets.append(encode_bytes_field(1, build_trace_packet(bundle)))

  # 3. The Custom Example Event
  bundle = encode_varint_field(1, 0)
  # This will be decomposed into 4 events at 2.01s, 2.02s, 2.03s, 2.04s
  bundle += encode_bytes_field(
      2,
      build_ftrace_event(
          2000000000, pid, payload_bytes=build_example_payload()))
  packets.append(encode_bytes_field(1, build_trace_packet(bundle)))

  with open("test_example.perfetto-trace", "wb") as f:
    for p in packets:
      f.write(p)

  print("Generated test_example.perfetto-trace")


if __name__ == "__main__":
  main()
