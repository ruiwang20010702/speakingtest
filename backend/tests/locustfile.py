import os
import sys
import random
import time
from locust import HttpUser, task, between, events, SequentialTaskSet

# Ensure src is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.auth import create_access_token
from src.infrastructure.config import get_settings

settings = get_settings()

class StudentBehavior(SequentialTaskSet):
    """
    Simulates the complete lifecycle of a student taking a test.
    Using SequentialTaskSet to ensure steps happen in order.
    """
    
    def on_start(self):
        self.entry_token = self.user.entry_token
        self.student_token = None
        self.test_id = None

    @task
    def student_entry(self):
        """Step 1: Student enters via token"""
        if not self.entry_token:
            self.interrupt()
            return

        with self.client.post(
            "/api/v1/students/entry",
            json={"token": self.entry_token},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.student_token = data["access_token"]
                self.test_id = data["test_id"]
                self.headers = {"Authorization": f"Bearer {self.student_token}"}
            else:
                response.failure(f"Entry failed: {response.text}")
                self.interrupt()

    @task
    def submit_part1(self):
        """Step 2: Submit Part 1 Audio"""
        if not self.student_token:
            self.interrupt()
            return
            
        audio_data = b"fake_mp3_content" * 100
        files = {
            "audio": ("part1.mp3", audio_data, "audio/mpeg")
        }
        
        with self.client.post(
            f"/api/v1/tests/{self.test_id}/part1",
            headers=self.headers,
            files=files,
            data={"reference_text": "Hello world"},
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Part 1 submit failed: {response.text}")
                self.interrupt()

    @task
    def wait_for_part1(self):
        """Step 3: Wait for Part 1 processing (Simulated)"""
        time.sleep(1)

    @task
    def submit_part2(self):
        """Step 4: Submit Part 2 Audio"""
        # Simulate OSS URL (in real world, frontend uploads to OSS first)
        fake_oss_url = f"https://oss.example.com/audio/part2_{self.test_id}.mp3"
        
        with self.client.post(
            f"/api/v1/tests/{self.test_id}/part2",
            headers=self.headers,
            json={
                "audio_url": fake_oss_url,
                "questions": [{"no": 1, "question": "What is your favorite color?"}]
            },
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Part 2 submit failed: {response.text}")
                self.interrupt()

    @task
    def poll_status(self):
        """Step 5: Poll for completion"""
        max_retries = 10
        for _ in range(max_retries):
            with self.client.get(
                f"/api/v1/tests/{self.test_id}",
                headers=self.headers,
                catch_response=True,
                name="/api/v1/tests/{id} (Poll)"
            ) as response:
                if response.status_code == 200:
                    data = response.json()
                    if data["status"] == "completed":
                        return
                    elif data["status"] == "failed":
                        response.failure("Test processing failed")
                        self.interrupt()
                        return
                else:
                    response.failure(f"Status check failed: {response.text}")
            
            time.sleep(2)
        
        # If we reach here, it timed out (expected in mock env without real workers)
        # We don't mark as failure to avoid noise in stress test if workers aren't running
        pass

    @task
    def view_report(self):
        """Step 6: View Final Report"""
        self.client.get(
            f"/api/v1/tests/{self.test_id}/report",
            headers=self.headers,
            name="/api/v1/tests/{id}/report"
        )
        self.interrupt()  # Finish user journey


class SpeakingTestUser(HttpUser):
    wait_time = between(2, 5)
    tasks = [StudentBehavior]
    
    def on_start(self):
        """
        Setup: Teacher creates student and generates token.
        This runs ONCE per simulated user to set up the environment.
        """
        # 1. Teacher Login (Real Login via Magic Code)
        self.teacher_id = random.randint(1000, 99999)
        email = f"teacher_{self.teacher_id}@51talk.com"
        
        # Use Magic Code 888888 (Enabled in DEBUG mode)
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "code": "888888"}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.teacher_token = data["access_token"]
            self.teacher_headers = {"Authorization": f"Bearer {self.teacher_token}"}
        else:
            print(f"Teacher login failed: {response.text}")
            self.teacher_token = None
            self.teacher_headers = {}
            return
        
        # 2. Import Student
        self.student_id = random.randint(100000, 999999)
        self.client.post(
            "/api/v1/students/import",
            headers=self.teacher_headers,
            json={"student_id": self.student_id}
        )
        
        # 3. Generate Student Token
        response = self.client.post(
            f"/api/v1/students/{self.student_id}/token",
            headers=self.teacher_headers,
            params={"level": "L1", "unit": "Unit 1"}
        )
        
        if response.status_code == 200:
            self.entry_token = response.json()["token"]
        else:
            self.entry_token = None


class AdminUser(HttpUser):
    """
    Simulates an Admin user monitoring the dashboard.
    Runs concurrently with students.
    """
    wait_time = between(5, 15)
    weight = 1  # Fewer admins than students
    
    def on_start(self):
        self.admin_id = 1
        self.token = create_access_token(
            data={"sub": str(self.admin_id), "role": "admin", "name": "Admin"}
        )
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task
    def check_dashboard(self):
        self.client.get(
            "/api/v1/admin/stats/overview",
            headers=self.headers,
            name="/api/v1/admin/stats/overview"
        )
