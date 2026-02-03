import logging
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

logger = logging.getLogger(__name__)

# =============================================================================
# Upstox V2 Market Data Protobuf Definitions
# =============================================================================
# This defines the Protobuf structure programmatically to avoid needing .proto files

_sym_db = _symbol_database.Default()

DESCRIPTOR = _descriptor.FileDescriptor(
    name='market_data_feed.proto',
    package='com.upstox.marketdata.rpc.proto',
    syntax='proto3',
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
    serialized_pb=b'\n\x16market_data_feed.proto\x12\x1f\x63om.upstox.marketdata.rpc.proto\"\xb0\x02\n\x0c\x46\x65\x65\x64Response\x12\x43\n\x04type\x18\x01 \x01(\x0e\x32\x35.com.upstox.marketdata.rpc.proto.FeedResponse.Type\x12J\n\x05\x66\x65\x65\x64s\x18\x02 \x03(\x0b\x32;.com.upstox.marketdata.rpc.proto.FeedResponse.FeedsEntry\x1aG\n\nFeedsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12(\n\x05value\x18\x02 \x01(\x0b\x32\x19.com.upstox.marketdata.rpc.proto.Feed:\x02\x38\x01\"&\n\x04Type\x12\x10\n\x0cinitial_feed\x10\x00\x12\x0c\n\x08live_feed\x10\x01\"m\n\x04\x46\x65\x65\x64\x12\x35\n\x03ltp\x18\x01 \x01(\x0b\x32(.com.upstox.marketdata.rpc.proto.LtpV2H\x00\x12\x36\n\x04\x66ull\x18\x02 \x01(\x0b\x32).com.upstox.marketdata.rpc.proto.FullV2H\x00\x42\x06\n\x04\x64\x61ta\"\'\n\x05LtpV2\x12\x0c\n\x04ltp\x18\x01 \x01(\x01\x12\x10\n\x08ltp_time\x18\x02 \x01(\x03\"\xf7\x01\n\x06\x46ullV2\x12\x35\n\x03ltp\x18\x01 \x01(\x0b\x32(.com.upstox.marketdata.rpc.proto.LtpV2\x12<\n\x04ohlc\x18\x02 \x01(\x0b\x32..com.upstox.marketdata.rpc.proto.MarketOHLCV2\x12\x14\n\x0clast_trd_qty\x18\x03 \x01(\x03\x12\x14\n\x0ctotal_buy_qty\x18\x04 \x01(\x01\x12\x15\n\rtotal_sell_qty\x18\x05 \x01(\x01\x12\x0e\n\x06volume\x18\x06 \x01(\x03\x12\x0b\n\x03\x61tp\x18\x07 \x01(\x01\x12\x0b\n\x03\x63oi\x18\x08 \x01(\x03\x12\x1b\n\x13\x63hange_percent_24hr\x18\t \x01(\x01\"G\n\x0cMarketOHLCV2\x12\x0c\n\x04open\x18\x01 \x01(\x01\x12\x0c\n\x04high\x18\x02 \x01(\x01\x12\x0b\n\x03low\x18\x03 \x01(\x01\x12\x0e\n\x06\x63lose\x18\x04 \x01(\x01\x62\x06proto3'
)

_FEEDRESPONSE_TYPE = _descriptor.EnumDescriptor(
  name='Type',
  full_name='com.upstox.marketdata.rpc.proto.FeedResponse.Type',
  filename=None,
  file=DESCRIPTOR,
  create_key=_descriptor._internal_create_key,
  values=[
    _descriptor.EnumValueDescriptor(
      name='initial_feed', index=0, number=0,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='live_feed', index=1, number=1,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=310,
  serialized_end=348,
)
_sym_db.RegisterEnumDescriptor(_FEEDRESPONSE_TYPE)


_FEEDRESPONSE_FEEDSENTRY = _descriptor.Descriptor(
  name='FeedsEntry',
  full_name='com.upstox.marketdata.rpc.proto.FeedResponse.FeedsEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='com.upstox.marketdata.rpc.proto.FeedResponse.FeedsEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value', full_name='com.upstox.marketdata.rpc.proto.FeedResponse.FeedsEntry.value', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=b'8\001',
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=237,
  serialized_end=308,
)

_FEEDRESPONSE = _descriptor.Descriptor(
  name='FeedResponse',
  full_name='com.upstox.marketdata.rpc.proto.FeedResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='type', full_name='com.upstox.marketdata.rpc.proto.FeedResponse.type', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='feeds', full_name='com.upstox.marketdata.rpc.proto.FeedResponse.feeds', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[_FEEDRESPONSE_FEEDSENTRY, ],
  enum_types=[
    _FEEDRESPONSE_TYPE,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=60,
  serialized_end=348,
)


_FEED = _descriptor.Descriptor(
  name='Feed',
  full_name='com.upstox.marketdata.rpc.proto.Feed',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='ltp', full_name='com.upstox.marketdata.rpc.proto.Feed.ltp', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='full', full_name='com.upstox.marketdata.rpc.proto.Feed.full', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
    _descriptor.OneofDescriptor(
      name='data', full_name='com.upstox.marketdata.rpc.proto.Feed.data',
      index=0, containing_type=None,
      create_key=_descriptor._internal_create_key,
    fields=[]),
  ],
  serialized_start=350,
  serialized_end=459,
)


_LTPV2 = _descriptor.Descriptor(
  name='LtpV2',
  full_name='com.upstox.marketdata.rpc.proto.LtpV2',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='ltp', full_name='com.upstox.marketdata.rpc.proto.LtpV2.ltp', index=0,
      number=1, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='ltp_time', full_name='com.upstox.marketdata.rpc.proto.LtpV2.ltp_time', index=1,
      number=2, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=461,
  serialized_end=500,
)


_FULLV2 = _descriptor.Descriptor(
  name='FullV2',
  full_name='com.upstox.marketdata.rpc.proto.FullV2',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='ltp', full_name='com.upstox.marketdata.rpc.proto.FullV2.ltp', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='ohlc', full_name='com.upstox.marketdata.rpc.proto.FullV2.ohlc', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='last_trd_qty', full_name='com.upstox.marketdata.rpc.proto.FullV2.last_trd_qty', index=2,
      number=3, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='total_buy_qty', full_name='com.upstox.marketdata.rpc.proto.FullV2.total_buy_qty', index=3,
      number=4, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='total_sell_qty', full_name='com.upstox.marketdata.rpc.proto.FullV2.total_sell_qty', index=4,
      number=5, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='volume', full_name='com.upstox.marketdata.rpc.proto.FullV2.volume', index=5,
      number=6, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='atp', full_name='com.upstox.marketdata.rpc.proto.FullV2.atp', index=6,
      number=7, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='coi', full_name='com.upstox.marketdata.rpc.proto.FullV2.coi', index=7,
      number=8, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='change_percent_24hr', full_name='com.upstox.marketdata.rpc.proto.FullV2.change_percent_24hr', index=8,
      number=9, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=503,
  serialized_end=750,
)


_MARKETOHLCV2 = _descriptor.Descriptor(
  name='MarketOHLCV2',
  full_name='com.upstox.marketdata.rpc.proto.MarketOHLCV2',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='open', full_name='com.upstox.marketdata.rpc.proto.MarketOHLCV2.open', index=0,
      number=1, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='high', full_name='com.upstox.marketdata.rpc.proto.MarketOHLCV2.high', index=1,
      number=2, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='low', full_name='com.upstox.marketdata.rpc.proto.MarketOHLCV2.low', index=2,
      number=3, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='close', full_name='com.upstox.marketdata.rpc.proto.MarketOHLCV2.close', index=3,
      number=4, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR, create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=752,
  serialized_end=823,
)

_FEEDRESPONSE_FEEDSENTRY.fields_by_name['value'].message_type = _FEED
_FEEDRESPONSE_FEEDSENTRY.containing_type = _FEEDRESPONSE
_FEEDRESPONSE.fields_by_name['type'].enum_type = _FEEDRESPONSE_TYPE
_FEEDRESPONSE.fields_by_name['feeds'].message_type = _FEEDRESPONSE_FEEDSENTRY
_FEED.fields_by_name['ltp'].message_type = _LTPV2
_FEED.fields_by_name['full'].message_type = _FULLV2
_FEED.oneofs_by_name['data'].fields.append(
  _FEED.fields_by_name['ltp'])
_FEED.fields_by_name['ltp'].containing_oneof = _FEED.oneofs_by_name['data']
_FEED.oneofs_by_name['data'].fields.append(
  _FEED.fields_by_name['full'])
_FEED.fields_by_name['full'].containing_oneof = _FEED.oneofs_by_name['data']
_FULLV2.fields_by_name['ltp'].message_type = _LTPV2
_FULLV2.fields_by_name['ohlc'].message_type = _MARKETOHLCV2
DESCRIPTOR.message_types_by_name['FeedResponse'] = _FEEDRESPONSE
DESCRIPTOR.message_types_by_name['Feed'] = _FEED
DESCRIPTOR.message_types_by_name['LtpV2'] = _LTPV2
DESCRIPTOR.message_types_by_name['FullV2'] = _FULLV2
DESCRIPTOR.message_types_by_name['MarketOHLCV2'] = _MARKETOHLCV2
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

FeedResponse = _reflection.GeneratedProtocolMessageType('FeedResponse', (_message.Message,), {
  'FeedsEntry' : _reflection.GeneratedProtocolMessageType('FeedsEntry', (_message.Message,), {
    'DESCRIPTOR' : _FEEDRESPONSE_FEEDSENTRY,
    '__module__' : 'market_data_feed_pb2'
    # @@protoc_insertion_point(class_scope:com.upstox.marketdata.rpc.proto.FeedResponse.FeedsEntry)
    })
  ,
  'DESCRIPTOR' : _FEEDRESPONSE,
  '__module__' : 'market_data_feed_pb2'
  # @@protoc_insertion_point(class_scope:com.upstox.marketdata.rpc.proto.FeedResponse)
  })
_sym_db.RegisterMessage(FeedResponse)
_sym_db.RegisterMessage(FeedResponse.FeedsEntry)

Feed = _reflection.GeneratedProtocolMessageType('Feed', (_message.Message,), {
  'DESCRIPTOR' : _FEED,
  '__module__' : 'market_data_feed_pb2'
  # @@protoc_insertion_point(class_scope:com.upstox.marketdata.rpc.proto.Feed)
  })
_sym_db.RegisterMessage(Feed)

LtpV2 = _reflection.GeneratedProtocolMessageType('LtpV2', (_message.Message,), {
  'DESCRIPTOR' : _LTPV2,
  '__module__' : 'market_data_feed_pb2'
  # @@protoc_insertion_point(class_scope:com.upstox.marketdata.rpc.proto.LtpV2)
  })
_sym_db.RegisterMessage(LtpV2)

FullV2 = _reflection.GeneratedProtocolMessageType('FullV2', (_message.Message,), {
  'DESCRIPTOR' : _FULLV2,
  '__module__' : 'market_data_feed_pb2'
  # @@protoc_insertion_point(class_scope:com.upstox.marketdata.rpc.proto.FullV2)
  })
_sym_db.RegisterMessage(FullV2)

MarketOHLCV2 = _reflection.GeneratedProtocolMessageType('MarketOHLCV2', (_message.Message,), {
  'DESCRIPTOR' : _MARKETOHLCV2,
  '__module__' : 'market_data_feed_pb2'
  # @@protoc_insertion_point(class_scope:com.upstox.marketdata.rpc.proto.MarketOHLCV2)
  })
_sym_db.RegisterMessage(MarketOHLCV2)


def decode_market_data(binary_data):
    """
    Decodes binary Protobuf data from Upstox V2 WebSocket.
    
    Returns:
        Dict mapping instrument_key to tick data.
    """
    try:
        response = FeedResponse()
        response.ParseFromString(binary_data)
        
        result = {}
        for key, feed in response.feeds.items():
            tick = {"instrument_key": key}
            
            # Extract ltp
            if feed.HasField("ltp"):
                tick["last_price"] = feed.ltp.ltp
                tick["ltp_time"] = feed.ltp.ltp_time
            elif feed.HasField("full"):
                tick["last_price"] = feed.full.ltp.ltp
                tick["ltp_time"] = feed.full.ltp.ltp_time
                tick["ohlc"] = {
                    "open": feed.full.ohlc.open,
                    "high": feed.full.ohlc.high,
                    "low": feed.full.ohlc.low,
                    "close": feed.full.ohlc.close
                }
                tick["volume"] = feed.full.volume
                tick["change_percent"] = feed.full.change_percent_24hr
            
            result[key] = tick
            
        return result
    except Exception as e:
        logger.error(f"Failed to decode Upstox Protobuf: {e}")
        return {}
