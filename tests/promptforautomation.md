Act as a Senior QA Automation & Performance Engineer specializing in multiplayer game testing. 

I need a runnable, automated concurrency/load-testing script to simulate 10 to 15 concurrent players joining and actively playing my multiplayer game, "Organic Battle", simultaneously in a single session.

### Technical Context & Architecture:
- Game Type: Real-time multiplayer ("Organic Battle")
- Client/Server Protocol: [Insert Protocol: e.g., WebSockets, Socket.io, HTTP polling, gRPC, or custom TCP/UDP]
- Server URL / Endpoint: [Insert Server Address, e.g., ws://localhost:8080 or http://localhost:3000]
- Tech Stack / Language for Test: [Insert preference: e.g., Node.js with ws/Socket.io-client, Python with asyncio/websockets, or k6/Playwright]

### Required Simulation Behavior:
1. Orchestration:
   - Spawn 10 to 15 virtual player instances concurrently (configurable pool size).
   - Have each virtual player authenticate/join the lobby, enter matchmaking/room, and transition to the active game state simultaneously.
2. Gameplay Loop Simulation:
   - Each player must execute valid in-game actions continuously (e.g., movement vectors, organic cell growth/split/attack inputs, ping/heartbeat) at typical human or tick rates (e.g., 10–30 updates/sec).
   - Simulate typical player jitter and action variability so not all requests hit on the exact same millisecond.
3. Chaos / Stress Edge Cases:
   - Simulate at least 1–2 players experiencing minor packet loss, rapid action bursts, or temporary disconnections/reconnections to check how the server handles degraded client states.

### Metrics & Diagnostic Checks to Track:
- Error Detection: Capture protocol-level errors, dropped sockets, unhandled server exceptions, state desynchronization, and rejected player commands.
- Latency & Delay: Measure Round-Trip Time (RTT) per action/tick, event delivery delay, and identify latency spikes (>100ms, >250ms).
- Throughput & Stability: Track messages sent/received per second, tick-rate stability, and dropped game states.
- Success/Failure Exit Criteria: Assert zero fatal disconnects, error rate < 1%, and 95th percentile latency below an acceptable threshold (e.g., < 150ms).

### Deliverables Needed:
1. Complete, executable test script with minimal external dependencies.
2. Step-by-step instructions on how to install dependencies, configure environment variables, and run the test locally or against a staging server.
3. A formatted console summary report printed at the end of the test run showing pass/fail status, key metrics (min/avg/p95 latency, error count, throughput), and actionable logs for any failed player instance.