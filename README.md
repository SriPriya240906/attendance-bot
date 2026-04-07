# RIT Chennai IMS Attendance Automation

This Python agent logs into the RIT Chennai IMS portal, captures the attendance page screenshot, and sends it to Telegram every day at 3:30 PM IST.

## Project Structure

- `main.py` — scheduler and run loop
- `scraper.py` — Playwright IMS automation and screenshot capture
- `bot.py` — Telegram message/photo sending
- `config.py` — environment loading and logging configuration
- `requirements.txt` — Python dependencies
- `.env.example` — environment variable template
- `logs/app.log` — runtime log file
- `screenshots/` — saved screenshots

## Installation

1. Open PowerShell in the project folder:
   ```powershell
   cd C:\Users\msrip\OneDrive\Desktop\agent
   ```
2. Create a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Install Playwright browsers:
   ```powershell
   python -m playwright install chromium
   ```
5. Copy `.env.example` to `.env` and fill in your values.

## Environment Variables

Create `.env` with:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
IMS_USERNAME=your_username
IMS_PASSWORD=your_password
```

## Running

### Start the scheduler continuously

```powershell
python .\main.py
```

### Run immediately (manual trigger)

```powershell
python .\main.py --run-now
```

## Windows Continuous Run Options

- Keep the PowerShell window open
- Or use `Start-Job` / Task Scheduler to run `python .\main.py`
- Example Task Scheduler command:
  ```powershell
  python C:\Users\msrip\OneDrive\Desktop\agent\main.py
  ```

## Notes

- Credentials are loaded from `.env` only.
- Logs are written to `logs/app.log`.
- The agent keeps the most recent 7 screenshots in `screenshots/`.
- On failure, the agent retries login and sends an error message to Telegram if capture fails.
