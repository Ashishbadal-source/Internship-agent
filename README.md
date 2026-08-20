# Internship Agent

Free daily internship finder using GitHub Actions and Telegram.

It searches public job APIs, applies hard filters, ranks matches against your profile, and sends the best 15-20 jobs to Telegram.

Sources:
- Adzuna for India and broader listings when API credentials are configured
- Remotive for remote jobs
- Jobicy for remote jobs
- Arbeitnow for additional public listings

No Claude API key is required. Ranking is local and deterministic.

## Setup

1. Create a Telegram bot with BotFather.
2. Send one message to your bot.
3. Open `https://api.telegram.org/botYOUR_TOKEN/getUpdates` and copy the numeric `chat.id`.
4. Put the bot token and chat ID into GitHub repository secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. Optional but strongly recommended for India coverage:
   - `ADZUNA_APP_ID`
   - `ADZUNA_APP_KEY`
6. Edit `profile/candidate.json` with your current skills and target preferences.
7. Push the repository to GitHub.
8. Enable Actions. The workflow runs every day at 8:00 AM IST and can also be started manually.

GitHub Actions now supports timezone-aware scheduled workflows, so the workflow uses `Asia/Kolkata`.

## Hard filters

- Pure Backend Developer roles are rejected.
- Explicit stipend/compensation at or below ₹20,000/month is rejected.
- On-site: maximum 2 months and must fit June-July.
- Hybrid: maximum 3 months and must fit June-August.
- Remote: duration must be less than 8 months.
- Missing stipend does not cause rejection by itself.

The source APIs have different coverage. No free public API reliably mirrors every LinkedIn posting, so this agent does not pretend to provide complete LinkedIn coverage.
