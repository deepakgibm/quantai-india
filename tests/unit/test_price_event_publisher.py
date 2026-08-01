import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from services.price_manager.price_event_publisher import PriceEventPublisher, get_price_event_publisher

@pytest.fixture
def publisher():
    with patch('services.price_manager.price_event_publisher.get_cache_manager') as mock_get_cache, \
         patch.object(PriceEventPublisher, 'start_listener'):
        mock_mgr = MagicMock()
        mock_mgr.is_available.return_value = False
        mock_get_cache.return_value = mock_mgr
        pub = PriceEventPublisher()
        yield pub
        pub.stop()

def test_subscribe_unsubscribe(publisher):
    cb1 = MagicMock()
    cb2 = MagicMock()
    
    publisher.subscribe_local(cb1)
    assert cb1 in publisher._local_subscribers
    assert len(publisher._local_subscribers) == 1
    
    publisher.subscribe_local(cb1)
    assert len(publisher._local_subscribers) == 1
    
    publisher.subscribe_local(cb2)
    assert cb2 in publisher._local_subscribers
    assert len(publisher._local_subscribers) == 2
    
    publisher.unsubscribe_local(cb1)
    assert cb1 not in publisher._local_subscribers
    assert cb2 in publisher._local_subscribers
    
    publisher.unsubscribe_local(cb1)

def test_publish_local_success_and_exception(publisher):
    cb_success = MagicMock()
    cb_fail = MagicMock(side_effect=Exception("Subscriber crashed"))
    
    publisher.subscribe_local(cb_success)
    publisher.subscribe_local(cb_fail)
    
    price_data = {"ltp": 150.0, "timestamp": "2026-07-25T00:00:00Z"}
    
    publisher.publish("INFY", price_data)
    
    cb_success.assert_called_once_with({
        "symbol": "INFY",
        "price_data": price_data,
        "timestamp": "2026-07-25T00:00:00Z"
    })
    cb_fail.assert_called_once()

@pytest.mark.asyncio
async def test_publish_redis_sync_and_async(publisher):
    publisher._cache_mgr.is_available.return_value = True
    
    mock_client = MagicMock()
    publisher._cache_mgr._client = mock_client
    
    mock_client._async_client = None
    mock_client._sync_client = MagicMock()
    
    price_data = {"ltp": 200.0}
    publisher.publish("TCS", price_data)
    mock_client._sync_client.publish.assert_called_once()
    
    mock_client._async_client = AsyncMock()
    mock_client._sync_client = None
    
    with patch('asyncio.create_task') as mock_create_task:
        publisher.publish("RELIANCE", price_data)
        mock_create_task.assert_called_once()

@pytest.mark.asyncio
async def test_publish_redis_async_execution(publisher):
    mock_client = AsyncMock()
    publisher._cache_mgr._client._async_client = mock_client
    
    payload = {"symbol": "SBIN", "price_data": {"ltp": 500.0}}
    await publisher._publish_redis_async(payload)
    
    mock_client.publish.assert_called_once_with(
        PriceEventPublisher.CHANNEL_NAME,
        json.dumps(payload)
    )

@pytest.mark.asyncio
async def test_publish_redis_async_exception(publisher):
    mock_client = AsyncMock()
    mock_client.publish.side_effect = Exception("Redis connection lost")
    publisher._cache_mgr._client._async_client = mock_client
    
    await publisher._publish_redis_async({"symbol": "SBIN"})

@pytest.mark.asyncio
async def test_redis_sub_loop_execution(publisher):
    publisher._cache_mgr.is_available.return_value = True
    
    mock_client = AsyncMock()
    mock_pubsub = AsyncMock()
    mock_client._async_client = mock_client
    mock_client.pubsub = MagicMock(return_value=mock_pubsub)
    publisher._cache_mgr._client = mock_client
    
    async def mock_get_message(*args, **kwargs):
        publisher._is_listening = False
        return {"type": "message", "data": json.dumps({"symbol": "TCS", "price_data": {"ltp": 3000.0}})}
        
    mock_pubsub.get_message.side_effect = mock_get_message
    
    local_cb = MagicMock()
    publisher._local_subscribers = [local_cb]
    publisher._is_listening = True
    
    with patch('services.price_manager.price_event_publisher.asyncio.sleep', new_callable=AsyncMock):
        await publisher._redis_sub_loop()
    
    local_cb.assert_called_with({"symbol": "TCS", "price_data": {"ltp": 3000.0}})

@pytest.mark.asyncio
async def test_redis_sub_loop_corrupt_json(publisher):
    publisher._cache_mgr.is_available.return_value = True
    mock_client = AsyncMock()
    mock_pubsub = AsyncMock()
    mock_client._async_client = mock_client
    mock_client.pubsub = MagicMock(return_value=mock_pubsub)
    publisher._cache_mgr._client = mock_client
    
    async def mock_get_message(*args, **kwargs):
        publisher._is_listening = False
        return {"type": "message", "data": "corrupt{invalid_json]"}
        
    mock_pubsub.get_message.side_effect = mock_get_message
    
    publisher._is_listening = True
    with patch('services.price_manager.price_event_publisher.asyncio.sleep', new_callable=AsyncMock):
        await publisher._redis_sub_loop()

def test_singleton_factory():
    pub1 = get_price_event_publisher()
    pub2 = get_price_event_publisher()
    assert pub1 is pub2
