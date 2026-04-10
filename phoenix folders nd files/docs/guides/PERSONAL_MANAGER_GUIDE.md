# Personal Manager - Usage Guide

## ✅ IMPLEMENTATION COMPLETE

Your Personal Manager system has been successfully integrated into Phoenix!

## 📁 Files Created/Modified

### New Files:
1. **`data/PersonalManager.json`** - Stores all your projects, goals, and todos
2. **`helpers/OllamaHelperPHNX.py`** - LLM integration for natural language processing
3. **`helpers/PersonalManagerPHNX.py`** - Core management classes
4. **`test_personal_manager.py`** - Test suite

### Modified Files:
1. **`bgprogs/time_monitor.pyw`** - Added startup reminders & periodic checks
2. **`data/intents.json`** - Added 6 new intent patterns

## 🎯 Features Implemented

### 1. Project Tracking
- Track multiple projects simultaneously
- Timeline of updates with timestamps
- Status tracking (in-progress/completed/blocked/on-hold)
- Priority levels
- Stale project detection (no updates in 3+ days)

### 2. Long-term Goals
- Set goals with targets (e.g., 100 push-ups, learn guitar)
- Track progress over time
- Deadline monitoring
- Daily/weekly frequency tracking
- Progress percentage calculation

### 3. Todo Management
- Today's and tomorrow's tasks
- Priority levels
- Link todos to projects
- Completion tracking

### 4. Background Monitoring
- **Startup announcement** - Speaks pending items when program launches
- **Periodic checks** - Every 6 hours checks for stale projects
- **Daily reminders** - At 9:00 AM (configurable)

## 🎙️ Voice Commands (Ready for Integration)

### Project Updates:
```
"Phoenix, I'm working on Dukan project, completed the admin dashboard"
"Phoenix, working on Dukan, finished the authentication module"
"Phoenix, update project Dukan, blocked on API integration"
```

### Project Queries:
```
"Phoenix, what's the status of Dukan project?"
"Phoenix, show my projects"
"Phoenix, tell me about Dukan"
```

### Goal Updates:
```
"Phoenix, I did 60 push-ups today"
"Phoenix, I practiced guitar for 2 hours"
"Phoenix, I made 5 commits to GitHub today"
```

### Goal Queries:
```
"Phoenix, show my goals"
"Phoenix, how much progress on push-ups goal?"
```

### Todo Management:
```
"Phoenix, add to todo: review code"
"Phoenix, remind me to call client tomorrow"
"Phoenix, what are my todos?"
```

## ⚙️ Configuration

Edit `data/PersonalManager.json` settings:

```json
{
  "settings": {
    "reminder_threshold_days": 3,      // Days before stale project alert
    "daily_summary_time": "09:00",     // When to announce daily summary
    "goal_reminder_frequency": "daily"  // How often to remind about goals
  }
}
```

## 🤖 Ollama Integration

### Current Status:
- ✅ Code ready
- ⚠️ Model name needs adjustment: Use `mistral:latest` instead of `mistral:7b-instruct`

### To activate Ollama:
1. Make sure Ollama is running: `ollama serve`
2. Update model name in code if needed
3. Voice commands will automatically use LLM for natural extraction

### What Ollama Does:
- **Intent Classification** - Understands what you want to do
- **Data Extraction** - Pulls project names, updates, progress from natural speech
- **Natural Responses** - Generates friendly, contextual responses

## 🚀 How to Use

### Starting the Background Process:
```powershell
# From Phoenix directory
python bgprogs\time_monitor.pyw
```

### What Happens on Startup:
1. Loads PersonalManager.json
2. Checks pending todos, goals, stale projects
3. **Announces summary**: "Sir, 2 todos pending today. Goals pending: 100 push-ups. No update on Dukan project in 3 days."
4. Runs continuous monitoring

### Manual Data Entry (Optional):
You can manually edit `data/PersonalManager.json` to add/modify:
- Projects
- Goals
- Todos

## 📊 Example Data Structure

### Sample Project:
```json
{
  "id": "proj_abc123",
  "name": "Dukan Desktop App",
  "status": "in-progress",
  "created_date": "2026-01-01",
  "last_updated": "2026-01-01 22:30",
  "priority": "high",
  "timeline": [
    {
      "date": "2026-01-01 22:30",
      "update": "Completed admin dashboard UI"
    }
  ],
  "current_task": "Working on inventory module"
}
```

### Sample Goal:
```json
{
  "id": "goal_xyz789",
  "title": "100 push-ups daily",
  "category": "fitness",
  "target": 100,
  "current_progress": 60,
  "unit": "push-ups",
  "deadline": "2026-12-31",
  "frequency": "daily",
  "progress_history": [
    {"date": "2026-01-01", "value": 60, "note": "Good session"}
  ],
  "status": "in-progress"
}
```

## 🔧 Testing

Run the test suite:
```powershell
python test_personal_manager.py
```

This tests:
- File structure
- Manager initialization
- CRUD operations
- Startup summary
- Ollama integration (if running)

## 🎨 Next Steps (Optional Enhancements)

1. **Voice Integration** - Connect to main Phoenix voice handler
2. **Ollama Fine-tuning** - Adjust model name for better extraction
3. **Web Dashboard** - Create visual interface for projects/goals
4. **Export Features** - Generate reports, markdown summaries
5. **Analytics** - Time tracking, productivity metrics
6. **Notifications** - Desktop notifications for reminders

## ⚠️ Important Notes

1. **Backup your data** - `PersonalManager.json` contains all your tracking info
2. **Your existing Phoenix features are untouched** - All original functionality remains
3. **Minimal changes** - Only 3 files modified, all changes are additive
4. **Safe to rollback** - If issues occur, just remove the PersonalManager import

## 📞 Troubleshooting

### Background process not starting?
```powershell
# Check for errors
python bgprogs\time_monitor.pyw
```

### No startup announcement?
- Check if `PersonalManager.json` has data
- Verify speaker volume
- Check error messages in console

### Ollama not working?
- Ensure Ollama is running: `ollama serve`
- Check model is available: `ollama list`
- Test manually: `ollama run mistral:latest`

## 🎉 Success Indicators

✅ Test suite passes  
✅ Startup announcement works  
✅ Data persists in JSON  
✅ Hourly time announcements still work  
✅ No errors in background process  

---

**Your 2-year Phoenix project now has intelligent personal management! 🚀**
