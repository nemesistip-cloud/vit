# Audit: Node Ecosystem (Track 9.3)

## What Exists
- `app/modules/network/models.py`: `NodeActivity` model which we've been using to track node states and registration history.
- `app/modules/network/node_types.py`: Defines "android" node type with a multiplier of 0.5.
- `app/modules/network/campus_node.py`: Implemented in 9.2, provides a pattern for registration and state tracking using `NodeActivity`.

## What's Missing
- `app/modules/network/android_node.py`: Specialized registration and heartbeat endpoints for mobile nodes.
- `app/modules/network/bandwidth.py`: Logic to track bandwidth contributions per node per epoch.
- `app/modules/network/mobile_relay.py`: Coordination for mobile relay nodes.

## What's Broken / Improvements Needed
- We need to ensure Android nodes respect the bandwidth caps specified in the build spec (100MB/day).
- Heartbeat mechanism needs to efficiently update node status without overloading the `NodeActivity` table if pings are frequent (every 5 mins).
- Bandwidth tracking requires a persistent way to store MB per epoch since `NodeActivity` is more of a generic log. I should check if there's a better place or if I should use `activity_meta` in a specific activity type.
