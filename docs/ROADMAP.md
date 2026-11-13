# Roadmap and limitations

Upstream: https://github.com/Jakeschincariol/day-trader-skill (MIT). Its README describes eleven Claude skills, with human approval before broker execution. Full line-by-line source audit remains pending.

## Implemented
Offline Python core with 15-minute opening range breakout signal, cash-constrained long-only paper positions, 1% planned per-trade risk, 3% aggregate planned risk, 5% realized daily loss gate, 10 position limit, simulated stop/target exits and basic tests.

## Not yet implemented
- Real-time market-data provider or 60-second scheduler
- Market holidays, stale data guard, persistence and restart recovery
- Mark-to-market daily drawdown guard and end-of-day liquidation
- Realistic spread, slippage, fees and partial fills
- Historical replay, statistical backtesting, dashboard, Claude API
- Integration of upstream 11 skills

Do not run unattended yet. This is an offline proof of concept, not a finished autonomous robot. No live brokerage interface exists.
