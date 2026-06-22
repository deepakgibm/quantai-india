# QuantAI Performance Hotspots

Top performance bottlenecks ranked by risk level and severity:

| Rank | Component | Bottleneck | Impact | Risk |
|------|-----------|------------|--------|------|
| 1 | OptionFlow Grid | React re-renders of 100+ rows on tick updates | High CPU / low FPS | Critical |
| 2 | DB Queries | JOINs on `instrument_master` for every candle load | 45ms DB block | High |
| 3 | Upstox REST | Sync fallbacks to Upstox API inside routers | Event loop blocking | High |
| 4 | WebSockets | Lack of heartbeat leads to zombie connections | Memory leaks | High |
| 5 | Cache | Lack of locking leads to cache stampedes | API latency spikes | Medium |
