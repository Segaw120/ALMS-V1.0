import sqlite3
import os
import logging

class WorldModelMemory:
    """
    Persistent state-tracking cache for RL environmental dynamics.
    Ensures RL agents don't make the same fundamental physics/economics
    mistakes across different Simulation Thought Lab sessions.
    """
    def __init__(self, db_path="world_model.db"):
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS global_lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    industry VARCHAR(50),
                    state_variable VARCHAR(100),
                    action_taken VARCHAR(50),
                    observed_outcome VARCHAR(200),
                    reward_delta FLOAT
                )
            ''')
            conn.commit()

    def cache_lesson(self, industry: str, state_variable: str, action: str, outcome: str, reward_delta: float):
        """Logs an environmental dynamic discovered by an RL agent."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO global_lessons (industry, state_variable, action_taken, observed_outcome, reward_delta)
                VALUES (?, ?, ?, ?, ?)
            ''', (industry, state_variable, action, outcome, reward_delta))
            conn.commit()
            logging.info(f"World Model Updated: {industry} | Action: {action} resulted in Delta: {reward_delta}")

    def fetch_lessons(self, industry: str):
        """Pulls prior learned dynamics to pre-condition new RL templates."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM global_lessons WHERE industry=?", (industry,))
            return cursor.fetchall()

    def fetch_all_lessons(self):
        """Pulls all prior learned dynamics across all industries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM global_lessons")
            return cursor.fetchall()
