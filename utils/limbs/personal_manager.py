"""
PersonalManagerPHNX.py - Manages Projects, Goals, and Todos
Provides CRUD operations and smart querying for personal tracking
"""

import os
import json
import uuid
from datetime import datetime, timedelta


class ProjectManager:
    """Manage projects and their timeline updates"""

    def __init__(self, data_file):
        self.data_file = data_file
        self.data = self._load_data()

    def _load_data(self):
        """Load data from JSON file"""
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading data: {e}")
            return {
                "projects": [],
                "goals": [],
                "todos": {"today": [], "tomorrow": [], "completed": []},
            }

    def _save_data(self):
        """Save data to JSON file"""
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False

    def find_project(self, project_name):
        """Find project by name (case-insensitive, fuzzy match)"""
        project_name_lower = project_name.lower().strip()

        for project in self.data.get("projects", []):
            if project_name_lower in project["name"].lower():
                return project
        return None

    def add_project(
        self, name, status="in-progress", priority="medium", deadline=None, tags=None
    ):
        """Create a new project"""
        project = {
            "id": f"proj_{uuid.uuid4().hex[:6]}",
            "name": name,
            "status": status,
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "priority": priority,
            "deadline": deadline,
            "tags": tags or [],
            "timeline": [],
            "current_task": "",
            "notes": "",
        }

        self.data.setdefault("projects", []).append(project)
        self._save_data()
        return project

    def update_project(self, project_name, update_text, status=None, current_task=None):
        """Add timeline entry to existing project or create new one"""
        project = self.find_project(project_name)

        if not project:
            # Create new project
            project = self.add_project(project_name)

        # Add timeline entry
        timeline_entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "update": update_text,
        }
        project["timeline"].append(timeline_entry)
        project["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        if status:
            project["status"] = status

        if current_task:
            project["current_task"] = current_task

        self._save_data()
        return project

    def get_project_info(self, project_name):
        """Get detailed project information"""
        project = self.find_project(project_name)

        if not project:
            return None

        # Get recent timeline entries (last 3)
        recent_updates = project["timeline"][-3:] if project["timeline"] else []

        return {
            "name": project["name"],
            "status": project["status"],
            "last_updated": project["last_updated"],
            "current_task": project["current_task"],
            "recent_updates": recent_updates,
            "priority": project["priority"],
        }

    def check_stale_projects(self, threshold_days=3):
        """Find projects with no updates in X days"""
        stale_projects = []
        current_date = datetime.now()

        for project in self.data.get("projects", []):
            if project["status"] != "completed":
                try:
                    last_updated = datetime.strptime(
                        project["last_updated"], "%Y-%m-%d %H:%M"
                    )
                    days_since_update = (current_date - last_updated).days

                    if days_since_update >= threshold_days:
                        stale_projects.append(
                            {
                                "name": project["name"],
                                "days_since_update": days_since_update,
                                "last_update": project["last_updated"],
                            }
                        )
                except Exception as e:
                    print(f"Error checking project {project['name']}: {e}")

        return stale_projects

    def list_active_projects(self):
        """Get all in-progress projects"""
        active = [
            p for p in self.data.get("projects", []) if p["status"] == "in-progress"
        ]
        return active


class GoalManager:
    """Manage long-term goals and track progress"""

    def __init__(self, data_file):
        self.data_file = data_file
        self.data = self._load_data()

    def _load_data(self):
        with open(self.data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_data(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False

    def find_goal(self, goal_name):
        """Find goal by name or category (fuzzy match)"""
        goal_name_lower = goal_name.lower().strip()

        for goal in self.data.get("goals", []):
            if (
                goal_name_lower in goal["title"].lower()
                or goal_name_lower in goal.get("category", "").lower()
            ):
                return goal
        return None

    def add_goal(self, title, category, target, unit, deadline, frequency="daily"):
        """Create a new goal"""
        goal = {
            "id": f"goal_{uuid.uuid4().hex[:6]}",
            "title": title,
            "category": category,
            "target": target,
            "current_progress": 0,
            "unit": unit,
            "deadline": deadline,
            "frequency": frequency,
            "started_date": datetime.now().strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "progress_history": [],
            "status": "in-progress",
        }

        self.data.setdefault("goals", []).append(goal)
        self._save_data()
        return goal

    def update_progress(self, goal_name, value, note=None):
        """Update goal progress"""
        goal = self.find_goal(goal_name)

        if not goal:
            return None

        # Add to progress history
        history_entry = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "value": value,
            "note": note or "",
        }
        goal["progress_history"].append(history_entry)
        goal["current_progress"] = value
        goal["last_updated"] = datetime.now().strftime("%Y-%m-%d")

        # Check if goal completed
        if value >= goal["target"]:
            goal["status"] = "completed"

        self._save_data()
        return goal

    def get_goal_status(self, goal_name):
        """Get goal status with progress percentage"""
        goal = self.find_goal(goal_name)

        if not goal:
            return None

        progress_percent = (
            (goal["current_progress"] / goal["target"] * 100)
            if goal["target"] > 0
            else 0
        )

        return {
            "title": goal["title"],
            "progress": goal["current_progress"],
            "target": goal["target"],
            "unit": goal["unit"],
            "progress_percent": round(progress_percent, 1),
            "status": goal["status"],
            "last_updated": goal["last_updated"],
        }

    def check_pending_goals(self):
        """Find goals that need attention today (based on frequency)"""
        pending = []
        current_date = datetime.now().date()

        for goal in self.data.get("goals", []):
            if goal["status"] != "completed":
                try:
                    last_updated = datetime.strptime(
                        goal["last_updated"], "%Y-%m-%d"
                    ).date()

                    # Check if update needed based on frequency
                    if goal["frequency"] == "daily" and last_updated < current_date:
                        pending.append(
                            {
                                "title": goal["title"],
                                "target": goal["target"],
                                "unit": goal["unit"],
                                "last_updated": goal["last_updated"],
                            }
                        )
                except Exception as e:
                    print(f"Error checking goal {goal['title']}: {e}")

        return pending

    def get_deadline_approaching(self, days_threshold=7):
        """Find goals with deadlines approaching"""
        approaching = []
        current_date = datetime.now().date()

        for goal in self.data.get("goals", []):
            if goal["status"] != "completed" and goal.get("deadline"):
                try:
                    deadline = datetime.strptime(goal["deadline"], "%Y-%m-%d").date()
                    days_remaining = (deadline - current_date).days

                    if 0 <= days_remaining <= days_threshold:
                        approaching.append(
                            {
                                "title": goal["title"],
                                "deadline": goal["deadline"],
                                "days_remaining": days_remaining,
                            }
                        )
                except Exception as e:
                    print(f"Error checking deadline for {goal['title']}: {e}")

        return approaching


class TodoManager:
    """Manage daily todos"""

    def __init__(self, data_file):
        self.data_file = data_file
        self.data = self._load_data()

    def _load_data(self):
        with open(self.data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_data(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False

    def add_todo(self, task, when="today", priority="medium", project_linked=None):
        """Add a new todo"""
        todo = {
            "id": f"todo_{uuid.uuid4().hex[:6]}",
            "task": task,
            "priority": priority,
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "project_linked": project_linked,
        }

        todos = self.data.setdefault(
            "todos", {"today": [], "tomorrow": [], "completed": []}
        )

        if when == "tomorrow":
            todos["tomorrow"].append(todo)
        else:
            todos["today"].append(todo)

        self._save_data()
        return todo

    def mark_completed(self, todo_id):
        """Mark todo as completed"""
        todos = self.data.get("todos", {})

        for todo in todos.get("today", []):
            if todo["id"] == todo_id:
                todo["completed"] = True
                todos["completed"].append(todo)
                todos["today"].remove(todo)
                self._save_data()
                return True

        return False

    def get_pending_todos(self, when="today"):
        """Get incomplete todos"""
        todos = self.data.get("todos", {})
        pending = [t for t in todos.get(when, []) if not t["completed"]]
        return pending

    def get_todo_summary(self):
        """Get count of pending/completed todos"""
        todos = self.data.get("todos", {})

        return {
            "today_pending": len(
                [t for t in todos.get("today", []) if not t["completed"]]
            ),
            "tomorrow_pending": len(todos.get("tomorrow", [])),
            "completed_today": len(
                [
                    t
                    for t in todos.get("completed", [])
                    if datetime.strptime(t["created_at"], "%Y-%m-%d %H:%M").date()
                    == datetime.now().date()
                ]
            ),
        }

    def move_overdue_todos(self):
        """Move yesterday's todos to today (called on startup)"""
        # This would be called by background process
        # For now, just returns status
        return {"status": "checked"}


class PersonalManager:
    """Main coordinator for all personal management"""

    def __init__(self, data_file=None):
        if data_file is None:
            data_file = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "PersonalManager.json"
            )

        self.data_file = data_file
        self.projects = ProjectManager(data_file)
        self.goals = GoalManager(data_file)
        self.todos = TodoManager(data_file)

        # Load settings
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.settings = data.get("settings", {})

    def get_startup_summary(self):
        """Get summary for startup announcement"""
        summary = {
            "pending_todos": self.todos.get_pending_todos("today"),
            "pending_goals": self.goals.check_pending_goals(),
            "stale_projects": self.projects.check_stale_projects(
                self.settings.get("reminder_threshold_days", 3)
            ),
            "approaching_deadlines": self.goals.get_deadline_approaching(),
        }
        return summary

    def format_startup_message(self, summary):
        """Format startup summary as speech text"""
        messages = []

        # Todos
        todo_count = len(summary["pending_todos"])
        if todo_count > 0:
            messages.append(
                f"{todo_count} todo{'s' if todo_count > 1 else ''} pending today"
            )

        # Goals
        goal_count = len(summary["pending_goals"])
        if goal_count > 0:
            goal_names = [g["title"] for g in summary["pending_goals"][:2]]
            messages.append(f"Goals pending: {', '.join(goal_names)}")

        # Stale projects
        if summary["stale_projects"]:
            stale = summary["stale_projects"][0]
            messages.append(
                f"No update on {stale['name']} project in {stale['days_since_update']} days"
            )

        if messages:
            return "Sir, " + ". ".join(messages) + "."
        else:
            return "All caught up, sir! No pending items."


# Standalone testing
if __name__ == "__main__":
    print("Testing PersonalManager...")

    pm = PersonalManager()

    # Test project management
    print("\n[TEST] Adding project...")
    proj = pm.projects.add_project("Test Project", priority="high")
    print(f"Created: {proj['name']}")

    print("\n[TEST] Updating project...")
    pm.projects.update_project("Test Project", "Initial setup completed")

    print("\n[TEST] Getting startup summary...")
    summary = pm.get_startup_summary()
    message = pm.format_startup_message(summary)
    print(f"Startup message: {message}")

    print("\n✅ All tests completed!")
