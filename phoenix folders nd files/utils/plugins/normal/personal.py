"""
Personal Plugin - Task Management (Projects, Goals, Todos)
===========================================================

Handles personal task management including projects, goals, and todos.
Wraps PersonalManagerPHNX.py functionality in plugin format.

Actions:
    - add_project: Create a new project
    - update_project: Update project status
    - add_todo: Add a todo item
    - complete_todo: Mark todo as done
    - add_goal: Create a new goal
    - update_goal: Update goal progress
    - get_summary: Get overall summary
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from ..base import BasePlugin


class PersonalPlugin(BasePlugin):
    """Plugin for personal task management."""

    PLUGIN_NAME = "personal"
    PLUGIN_DESCRIPTION = "Projects, goals, and todo management"

    def __init__(self, speech_engine=None, voice_recognition=None, config: dict = None):
        # Data file path
        phoenix_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.data_file = os.path.join(phoenix_root, "data", "PersonalManager.json")

        # Load data
        self.data = self._load_data()

        super().__init__(speech_engine, voice_recognition, config)

    def _load_data(self) -> dict:
        """Load data from JSON file."""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load personal data: {e}")

        # Default structure
        return {
            "projects": [],
            "goals": [],
            "todos": {"today": [], "tomorrow": [], "completed": []},
            "settings": {"reminder_threshold_days": 3},
        }

    def _save_data(self) -> bool:
        """Save data to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save personal data: {e}")
            return False

    def _register_actions(self) -> None:
        """Register all personal management actions."""
        # Projects
        self.register("add_project", self.add_project, "Create a new project")
        self.register("update_project", self.update_project, "Update project status")
        self.register("get_project", self.get_project, "Get project info")
        self.register("list_projects", self.list_projects, "List active projects")
        self.register(
            "check_stale", self.check_stale_projects, "Check for stale projects"
        )

        # Todos
        self.register("add_todo", self.add_todo, "Add a todo item")
        self.register("complete_todo", self.complete_todo, "Mark todo as complete")
        self.register("list_todos", self.list_todos, "List pending todos")
        self.register("get_todo_summary", self.get_todo_summary, "Get todo counts")

        # Goals
        self.register("add_goal", self.add_goal, "Create a new goal")
        self.register("update_goal", self.update_goal, "Update goal progress")
        self.register("get_goal", self.get_goal, "Get goal status")
        self.register("list_goals", self.list_goals, "List active goals")

        # Summary
        self.register("get_summary", self.get_startup_summary, "Get overall summary")
        self.register("morning_briefing", self.morning_briefing, "Get morning briefing")

    # ==================== Projects ====================

    def add_project(
        self, name: str, priority: str = "medium", deadline: str = None
    ) -> Dict:
        """
        Create a new project.

        Args:
            name: Project name
            priority: Priority level (low, medium, high)
            deadline: Optional deadline (YYYY-MM-DD)

        Returns:
            Created project dict
        """
        project = {
            "id": f"proj_{uuid.uuid4().hex[:6]}",
            "name": name,
            "status": "in-progress",
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "priority": priority,
            "deadline": deadline,
            "timeline": [],
            "current_task": "",
            "notes": "",
        }

        self.data.setdefault("projects", []).append(project)
        self._save_data()

        self.speak(f"Created project: {name}")
        return project

    def update_project(
        self, name: str, update_text: str, status: str = None
    ) -> Optional[Dict]:
        """
        Update a project with timeline entry.

        Args:
            name: Project name
            update_text: Update description
            status: Optional new status

        Returns:
            Updated project or None
        """
        project = self._find_project(name)

        if not project:
            # Create new project
            project = self.add_project(name)

        # Add timeline entry
        timeline_entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "update": update_text,
        }
        project["timeline"].append(timeline_entry)
        project["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        if status:
            project["status"] = status

        self._save_data()
        self.speak(f"Updated {name}")
        return project

    def _find_project(self, name: str) -> Optional[Dict]:
        """Find project by name (fuzzy match)."""
        name_lower = name.lower().strip()

        for project in self.data.get("projects", []):
            if name_lower in project["name"].lower():
                return project

        return None

    def get_project(self, name: str) -> Optional[Dict]:
        """Get project information."""
        project = self._find_project(name)

        if not project:
            self.speak(f"Couldn't find project: {name}")
            return None

        # Get recent updates
        recent = project["timeline"][-3:] if project["timeline"] else []

        return {
            "name": project["name"],
            "status": project["status"],
            "last_updated": project["last_updated"],
            "priority": project["priority"],
            "recent_updates": recent,
        }

    def list_projects(self) -> List[Dict]:
        """List all active projects."""
        active = [
            p for p in self.data.get("projects", []) if p["status"] == "in-progress"
        ]

        if active:
            names = [p["name"] for p in active]
            self.speak(
                f"You have {len(active)} active projects: {', '.join(names[:3])}"
            )
        else:
            self.speak("No active projects")

        return active

    def check_stale_projects(self, days: int = 3) -> List[Dict]:
        """Check for projects with no recent updates."""
        stale = []
        current_date = datetime.now()

        for project in self.data.get("projects", []):
            if project["status"] != "completed":
                try:
                    last_updated = datetime.strptime(
                        project["last_updated"], "%Y-%m-%d %H:%M"
                    )
                    days_since = (current_date - last_updated).days

                    if days_since >= days:
                        stale.append(
                            {
                                "name": project["name"],
                                "days_since_update": days_since,
                            }
                        )
                except Exception:
                    pass

        if stale:
            self.speak(f"You have {len(stale)} stale projects")

        return stale

    # ==================== Todos ====================

    def add_todo(
        self, task: str, when: str = "today", priority: str = "medium"
    ) -> Dict:
        """
        Add a todo item.

        Args:
            task: Task description
            when: "today" or "tomorrow"
            priority: Priority level

        Returns:
            Created todo dict
        """
        todo = {
            "id": f"todo_{uuid.uuid4().hex[:6]}",
            "task": task,
            "priority": priority,
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        todos = self.data.setdefault(
            "todos", {"today": [], "tomorrow": [], "completed": []}
        )

        if when == "tomorrow":
            todos["tomorrow"].append(todo)
        else:
            todos["today"].append(todo)

        self._save_data()
        self.speak(f"Added todo: {task}")
        return todo

    def complete_todo(self, task_id: str = None, task_text: str = None) -> bool:
        """
        Mark a todo as complete.

        Args:
            task_id: Todo ID (optional)
            task_text: Task description to match (optional)

        Returns:
            True if completed
        """
        todos = self.data.get("todos", {})

        for todo in todos.get("today", []):
            if task_id and todo["id"] == task_id:
                todo["completed"] = True
                todos["completed"].append(todo)
                todos["today"].remove(todo)
                self._save_data()
                self.speak("Todo completed")
                return True
            elif task_text and task_text.lower() in todo["task"].lower():
                todo["completed"] = True
                todos["completed"].append(todo)
                todos["today"].remove(todo)
                self._save_data()
                self.speak("Todo completed")
                return True

        self.speak("Couldn't find that todo")
        return False

    def list_todos(self, when: str = "today") -> List[Dict]:
        """List pending todos."""
        todos = self.data.get("todos", {})
        pending = [t for t in todos.get(when, []) if not t["completed"]]

        if pending:
            self.speak(f"You have {len(pending)} pending todos for {when}")
        else:
            self.speak(f"No pending todos for {when}")

        return pending

    def get_todo_summary(self) -> Dict:
        """Get count of pending and completed todos."""
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

    # ==================== Goals ====================

    def add_goal(
        self,
        title: str,
        target: int,
        unit: str,
        deadline: str = None,
        frequency: str = "daily",
    ) -> Dict:
        """
        Create a new goal.

        Args:
            title: Goal title
            target: Target value
            unit: Unit of measurement
            deadline: Optional deadline
            frequency: Update frequency (daily, weekly)

        Returns:
            Created goal dict
        """
        goal = {
            "id": f"goal_{uuid.uuid4().hex[:6]}",
            "title": title,
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

        self.speak(f"Created goal: {title}")
        return goal

    def update_goal(self, title: str, value: int, note: str = None) -> Optional[Dict]:
        """
        Update goal progress.

        Args:
            title: Goal title
            value: New progress value
            note: Optional note

        Returns:
            Updated goal or None
        """
        goal = self._find_goal(title)

        if not goal:
            self.speak(f"Couldn't find goal: {title}")
            return None

        # Add progress entry
        goal["progress_history"].append(
            {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "value": value,
                "note": note or "",
            }
        )
        goal["current_progress"] = value
        goal["last_updated"] = datetime.now().strftime("%Y-%m-%d")

        # Check completion
        if value >= goal["target"]:
            goal["status"] = "completed"
            self.speak(f"Congratulations! Goal {title} completed!")
        else:
            progress_pct = (value / goal["target"]) * 100
            self.speak(f"Updated {title}: {progress_pct:.0f}% complete")

        self._save_data()
        return goal

    def _find_goal(self, title: str) -> Optional[Dict]:
        """Find goal by title (fuzzy match)."""
        title_lower = title.lower().strip()

        for goal in self.data.get("goals", []):
            if title_lower in goal["title"].lower():
                return goal

        return None

    def get_goal(self, title: str) -> Optional[Dict]:
        """Get goal status."""
        goal = self._find_goal(title)

        if not goal:
            self.speak(f"Couldn't find goal: {title}")
            return None

        progress_pct = (
            (goal["current_progress"] / goal["target"]) * 100
            if goal["target"] > 0
            else 0
        )

        return {
            "title": goal["title"],
            "progress": goal["current_progress"],
            "target": goal["target"],
            "unit": goal["unit"],
            "progress_percent": round(progress_pct, 1),
            "status": goal["status"],
        }

    def list_goals(self) -> List[Dict]:
        """List active goals."""
        active = [g for g in self.data.get("goals", []) if g["status"] == "in-progress"]

        if active:
            self.speak(f"You have {len(active)} active goals")
        else:
            self.speak("No active goals")

        return active

    # ==================== Summary ====================

    def get_startup_summary(self) -> Dict:
        """Get summary for startup/briefing."""
        summary = {
            "pending_todos": self.list_todos("today"),
            "stale_projects": self.check_stale_projects(),
            "active_goals": self.list_goals(),
        }
        return summary

    def morning_briefing(self) -> str:
        """Generate morning briefing message."""
        messages = []

        # Todos
        todo_summary = self.get_todo_summary()
        if todo_summary["today_pending"] > 0:
            messages.append(f"{todo_summary['today_pending']} todos pending today")

        # Stale projects
        stale = self.check_stale_projects()
        if stale:
            messages.append(f"{len(stale)} projects need attention")

        # Goals
        active_goals = [
            g for g in self.data.get("goals", []) if g["status"] == "in-progress"
        ]
        if active_goals:
            messages.append(f"{len(active_goals)} goals in progress")

        if messages:
            briefing = "Good morning sir. " + ". ".join(messages) + "."
        else:
            briefing = "Good morning sir. All caught up! No pending items."

        self.speak(briefing)
        return briefing
