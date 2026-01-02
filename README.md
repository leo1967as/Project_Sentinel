# 🛡️ Project Sentinel

**The Guardian & Coach** - ระบบคุมวินัยการเทรดอัตโนมัติ (Anti-Gambling) และระบบวิเคราะห์ด้วย AI

## 🚀 Quick Start

```bash
# 1. Run setup (creates venv, installs deps, runs config wizard)
setup.bat

# 2. Start the guardian
run_guardian.bat
```

## 📁 Project Structure

```
Project_Sentinel/
├── active_block_monitor.py   # Risk Guardian - closes positions on max loss
├── data_collector.py         # Tick data & news collection
├── daily_report.py           # AI analysis & Line Notify reports
├── main_guardian.py          # Master controller (runs 24/7)
├── config.py                 # Secure configuration loader
├── config_setup.py           # Interactive setup wizard
│
├── utils/
│   └── mt5_connect.py        # MT5 connection manager
│
├── database/                 # SQLite tick & news data
├── logs/                     # Action logs & audit trail
├── charts/                   # Generated analysis charts
│
├── .env                      # Your config (NEVER commit!)
├── .env.example              # Template
├── requirements.txt          # Python dependencies
│
└── *.bat                     # Launcher scripts
```

## 🧩 Modules

### Module 1: Risk Guardian

**หน้าที่:** เฝ้าพอร์ต Real-time และ "ตบมือ" เมื่อคุณดื้อ

- ตรวจสอบ Daily P&L ทุก 5 วินาที
- เมื่อขาดทุนเกิน threshold → ปิดทุก Position ทันที
- **Active Block Mode:** ตรวจทุก 0.5 วินาที ถ้าเปิด Position ใหม่ → ปิดทันที!
- Reset เวลา 04:00 AM (ตาม Exness swap)

### Module 2: Data Collector

**หน้าที่:** เก็บข้อมูลสำหรับ AI วิเคราะห์

- บันทึก Tick Data (XAUUSD) ลง SQLite
- Batch insert ทุก 1000 ticks (ประหยัด memory)
- Scrape ForexFactory news ทุก 1 ชั่วโมง

### Module 3: AI Coach

**หน้าที่:** วิเคราะห์การเทรดให้ทุกเช้า

- รันตอน 05:00 AM (ตั้ง Task Scheduler)
- จัดกลุ่มเทรด "Battle" (15 นาที / $2)
- สร้างกราฟ matplotlib พร้อม Entry/Exit arrows
- ส่งให้ AI วิเคราะห์ผ่าน OpenRouter
- ส่งรายงานเข้า Line Notify

## ⚙️ Configuration

**ห้ามใส่ API Key ใน source code!** ใช้ `.env` file:

```bash
# Copy template
cp .env.example .env

# Edit with your values
notepad .env
```

**Required:**

- `MT5_LOGIN` - Account number
- `MT5_PASSWORD` - Account password
- `MT5_SERVER` - Server name

**Optional:**

- `OPENROUTER_API_KEY` - For AI analysis
- `LINE_NOTIFY_TOKEN` - For notifications

## 🔒 Security Features

- ✅ API keys in `.env` only (not in code)
- ✅ `.gitignore` prevents accidental commits
- ✅ Encrypted config backup (AES-256)
- ✅ Audit log for all config access
- ✅ Safe mode on config corruption

## 📊 Health Monitoring

Guardian exposes HTTP endpoint:

```bash
# Simple health check
curl http://localhost:8765/health

# Detailed status
curl http://localhost:8765/status
```

## 🛠️ Task Scheduler Setup

For daily report at 05:00 AM:

1. Open Task Scheduler
2. Create Basic Task: "Sentinel Daily Report"
3. Trigger: Daily at 05:00
4. Action: Start Program
   - Program: `D:\...\Project_Sentinel\run_report.bat`
   - Start in: `D:\...\Project_Sentinel`

## ⚠️ Important Notes

1. **TEST MODE:** เปิด `TEST_MODE=true` ก่อนใช้จริง!
2. **Demo First:** ทดสอบกับบัญชี Demo เสมอ
3. **Backup:** เก็บรักษา `.env` ไว้ที่อื่นด้วย
4. **Monitor:** ตรวจ logs เป็นประจำ

## 📝 License

Personal use only. Not for distribution.
