#!/usr/bin/env python3
"""
Generates a test .pftrace file containing a synthetic 'ggo' generic ftrace
event. The trace can be loaded in a locally-built Perfetto UI to verify that
FtraceTokenizer::TokenizeFtraceGgo correctly decomposes it into four
counter events with recalculated timestamps.

Proto wire format reference (field encoding):
  varint:  (field_number << 3) | 0
  len-del: (field_number << 3) | 2
"""

import struct
import sys

# ---------------------------------------------------------------------------
# Low-level protobuf helpers (wire format)
# ---------------------------------------------------------------------------


def encode_varint(value):
  """Encode an unsigned integer as a protobuf varint."""
  out = bytearray()
  while value > 0x7F:
    out.append((value & 0x7F) | 0x80)
    value >>= 7
  out.append(value & 0x7F)
  return bytes(out)


def encode_varint_field(field_number, value):
  """Encode a varint proto field (wire type 0)."""
  tag = encode_varint((field_number << 3) | 0)
  return tag + encode_varint(value)


def encode_bytes_field(field_number, data):
  """Encode a length-delimited proto field (wire type 2)."""
  tag = encode_varint((field_number << 3) | 2)
  return tag + encode_varint(len(data)) + data


def encode_string_field(field_number, s):
  """Encode a string proto field (wire type 2)."""
  return encode_bytes_field(field_number, s.encode('utf-8'))


# ---------------------------------------------------------------------------
# DescriptorProto / FieldDescriptorProto builders
# ---------------------------------------------------------------------------
# FieldDescriptorProto field numbers:
#   name   = 1 (string)
#   number = 3 (int32)
#   type   = 5 (enum Type)
#
# DescriptorProto field numbers:
#   name  = 1 (string)
#   field = 2 (repeated FieldDescriptorProto)

# Proto FieldDescriptorProto.Type enum values:
TYPE_INT64 = 3  # varint, int64
TYPE_INT32 = 5  # varint, int32
TYPE_UINT64 = 4  # varint, uint64


def make_field_descriptor(name, number, proto_type):
  """Build a serialised FieldDescriptorProto."""
  out = encode_string_field(1, name)  # name
  out += encode_varint_field(3, number)  # number
  out += encode_varint_field(5, proto_type)  # type
  return out


def build_ggo_descriptor():
  """
    Build a serialised DescriptorProto for the 'ggo' event with fields:
      1: base_timestamp  (int64)
      2: ts1             (int64)
      3: ts2             (int64)
      4: ts3             (int64)
      5: ts4             (int64)
      6: val1            (int32)
      7: val2            (int32)
      8: val3            (int32)
      9: val4            (int32)
    """
  out = encode_string_field(1, "ggo")  # DescriptorProto.name

  fields = [
      ("base_timestamp", 1, TYPE_INT64),
      ("ts1", 2, TYPE_INT64),
      ("ts2", 3, TYPE_INT64),
      ("ts3", 4, TYPE_INT64),
      ("ts4", 5, TYPE_INT64),
      ("val1", 6, TYPE_INT32),
      ("val2", 7, TYPE_INT32),
      ("val3", 8, TYPE_INT32),
      ("val4", 9, TYPE_INT32),
  ]
  for name, number, ftype in fields:
    fd = make_field_descriptor(name, number, ftype)
    out += encode_bytes_field(2, fd)  # DescriptorProto.field (repeated)

  return out


# ---------------------------------------------------------------------------
# The dynamic field ID used inside FtraceEvent for our 'ggo' payload.
# Must be >= 65536 (GenericFtraceTracker::kGenericEvtProtoMinPbFieldId).
# ---------------------------------------------------------------------------
GGO_FIELD_ID = 70000


def build_ggo_event_payload():
  """
    Serialise the ggo sub-message payload using the field numbers defined
    in our descriptor above.

    Example values:
      base_timestamp = 1_000_000_000 ns  (1 second)
      ts1 = 100_000 ns   -> event at 1_000_100_000 ns
      ts2 = 200_000 ns   -> event at 1_000_200_000 ns
      ts3 = 300_000 ns   -> event at 1_000_300_000 ns
      ts4 = 400_000 ns   -> event at 1_000_400_000 ns
      val1..val4 = 111, 222, 333, 444
    """
  out = encode_varint_field(1, 1_000_000_000)  # base_timestamp
  out += encode_varint_field(2, 100_000)  # ts1
  out += encode_varint_field(3, 200_000)  # ts2
  out += encode_varint_field(4, 300_000)  # ts3
  out += encode_varint_field(5, 400_000)  # ts4
  out += encode_varint_field(6, 111)  # val1
  out += encode_varint_field(7, 222)  # val2
  out += encode_varint_field(8, 333)  # val3
  out += encode_varint_field(9, 444)  # val4
  return out


def build_ftrace_event(timestamp_ns, pid, ggo_payload):
  """
    Build a serialised FtraceEvent:
      uint64 timestamp = 1
      uint32 pid       = 2
      <ggo payload at field GGO_FIELD_ID>
    """
  out = encode_varint_field(1, timestamp_ns)
  out += encode_varint_field(2, pid)
  out += encode_bytes_field(GGO_FIELD_ID, ggo_payload)
  return out


def build_generic_event_descriptor():
  """
    Build a serialised GenericEventDescriptor (inside FtraceEventBundle):
      int32 field_id        = 1
      bytes event_descriptor = 2   (serialised DescriptorProto)
    """
  out = encode_varint_field(1, GGO_FIELD_ID)
  out += encode_bytes_field(2, build_ggo_descriptor())
  return out


def build_ftrace_event_bundle_with_descriptor(cpu):
  """
    First bundle: contains only the GenericEventDescriptor (no events).
    This ensures the descriptor is registered before events are tokenised.

    FtraceEventBundle:
      uint32 cpu = 1
      repeated GenericEventDescriptor generic_event_descriptors = 11
    """
  out = encode_varint_field(1, cpu)
  out += encode_bytes_field(11, build_generic_event_descriptor())
  return out


def build_ftrace_event_bundle_with_event(cpu, ftrace_event):
  """
    Second bundle: contains the actual ggo FtraceEvent.

    FtraceEventBundle:
      uint32 cpu = 1
      repeated FtraceEvent event = 2
    """
  out = encode_varint_field(1, cpu)
  out += encode_bytes_field(2, ftrace_event)
  return out


def build_trace_packet(ftrace_bundle):
  """
    Wrap a FtraceEventBundle into a TracePacket.

    TracePacket:
      FtraceEventBundle ftrace_events = 1
    """
  return encode_bytes_field(1, ftrace_bundle)


def build_trace():
  """
    Construct the full trace file.

    Trace:
      repeated TracePacket packet = 1
    """
  cpu = 0
  pid = 1001

  # Packet 1: register the descriptor
  bundle1 = build_ftrace_event_bundle_with_descriptor(cpu)
  pkt1 = build_trace_packet(bundle1)

  # Packet 2: the ggo event
  # timestamp = 2_000_000_000 ns (2 seconds) — this is the FtraceEvent
  # header timestamp, which the tokeniser normally uses for clock
  # resolution.  Our TokenizeFtraceGgo will override with calculated
  # timestamps from the payload.
  ggo_payload = build_ggo_event_payload()
  event = build_ftrace_event(2_000_000_000, pid, ggo_payload)
  bundle2 = build_ftrace_event_bundle_with_event(cpu, event)
  pkt2 = build_trace_packet(bundle2)

  # Trace = repeated TracePacket (field 1)
  trace = encode_bytes_field(1, pkt1)
  trace += encode_bytes_field(1, pkt2)
  return trace


if __name__ == "__main__":
  data = build_trace()
  outfile = "test_ggo.pftrace"
  with open(outfile, "wb") as f:
    f.write(data)
  print(f"✅ 成功產生 {outfile} ({len(data)} bytes)")
  print(f"   GGO_FIELD_ID = {GGO_FIELD_ID}")
  print(f"   Descriptor bundle + 1 event bundle")
  print(f"   base_ts=1s, offsets=100/200/300/400 us, vals=111/222/333/444")
