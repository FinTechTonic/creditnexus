# Polymarket Surveillance Alerts – How It Works & Resolution Plan

## How it currently works

1. **GET /api/polymarket/surveillance/alerts**  
   - Returns alerts from the database table `polymarket_surveillance_alerts`.  
   - Alerts are **not** fetched from an external API; they are **generated** by the detection cycle and stored in the DB.

2. **Detection cycle (POST /api/polymarket/surveillance/run-cycle)**  
   - Runs only when `POLYMARKET_SURVEILLANCE_ENABLED=true`.  
   - Calls Polymarket Data API (trades, activity, leaderboard, volume, open-interest) via `POLYMARKET_DATA_API_URL`.  
   - Updates baselines and creates alerts when rules fire (e.g. wallet with ≥20 trades → "outsized_bet" alert).  
   - If `POLYMARKET_SURVEILLANCE_ENABLED` is false, the cycle returns `{"skipped": true}` and creates no alerts.

3. **Why the panel is empty**  
   - Default config: `POLYMARKET_SURVEILLANCE_ENABLED=false`, so the cycle is skipped.  
   - Even when enabled, alerts only appear after at least one successful run of the detection cycle.  
   - If `POLYMARKET_DATA_API_URL` is unset or the Data API returns empty/fails, the cycle creates no alerts.

## How it should work

- **Config:** Set `POLYMARKET_SURVEILLANCE_ENABLED=true` and `POLYMARKET_DATA_API_URL` (e.g. `https://data-api.polymarket.com`) when you want surveillance.  
- **Populate alerts:** Either call **POST /run-cycle** (e.g. "Run cycle" in the UI) or use the optional **GET /alerts?run_cycle_if_empty=1** (instance admin only) so the backend runs one cycle when the list is empty, then returns the list.  
- **Ongoing:** Run the cycle on a schedule (cron/scheduler) or manually so new alerts are created over time.

## Resolution plan (implemented)

1. **Backend**  
   - **GET /alerts** accepts optional `run_cycle_if_empty=1`. When the list is empty, the user is an instance admin, and `POLYMARKET_SURVEILLANCE_ENABLED` is true, the backend runs one detection cycle and then returns the (possibly updated) list.  
   - Instance admin = admin role, `is_instance_admin`, or first user.  
   - **Detection cycle** fetches each Data API endpoint in isolation (trades, activity, volume, open-interest); 400/404 on one does not break the cycle. Trades are always used when available.  
   - Wallet extraction from trade/activity items uses multiple field names: maker, taker, user, wallet, owner, trader, address, from, to.  
   - Threshold alert: wallet with ≥5 trades in the batch (lowered from 20 so alerts appear with sparse data).  
   - If the cycle fetches trades but no wallet crosses the threshold, one informational "cycle_completed" alert is created so the panel shows activity.

2. **Frontend**  
   - When the panel loads and the first response is an empty list (and not 403), it retries once with `run_cycle_if_empty=1` so instance admins can auto-populate without clicking "Run cycle".  
   - Empty state message explains that alerts come from the detection cycle and that `POLYMARKET_SURVEILLANCE_ENABLED` and `POLYMARKET_DATA_API_URL` must be set on the server.

3. **Checklist for operators**  
   - Set `POLYMARKET_SURVEILLANCE_ENABLED=true` and `POLYMARKET_DATA_API_URL` in `.env` when using surveillance.  
   - Ensure instance admins have access (admin role or `is_instance_admin` or first user).  
   - Run a detection cycle at least once (UI "Run cycle" or GET with `run_cycle_if_empty=1`) or schedule POST /run-cycle.  
   - Trades endpoint is required for alerts; activity/leaderboard/volume/open-interest are optional (400/404 are handled).
