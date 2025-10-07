#!/usr/bin/env python3
"""
Improved Comprehensive Backend API Testing for Resource Usage App
- Better error logging
- Random Copilot command testing
- Flexible summary refresh validation
"""

import requests
import sys
import os
from datetime import datetime, timedelta

from error_logger import log_error
from copilot_commands import get_random_command


class ResourceAppAPITester:
    def __init__(self, base_url="https://f2338967-2fb5-4159-8a60-e5a8da984108.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.created_resources = {
            'notes': [],
            'schedules': [],
            'summaries': []
        }
        self.api_key = "resource-app-copilot-key-2024"

    def log_test(self, name, success, details=""):
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def run_request(self, method, endpoint, data=None, files=None, expected_status=200):
        url = f"{self.base_url}/{endpoint}"
        headers = {"X-API-Key": self.api_key}
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, headers=headers, timeout=30)
                else:
                    headers = {**headers, "Content-Type": "application/json"}
                    response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                headers = {**headers, "Content-Type": "application/json"}
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            return success, response
        except Exception as e:
            print(f"Request error: {str(e)}")
            return False, None

    # ---------------- Connectivity ----------------
    def test_connection_status(self):
        success, response = self.run_request('GET', 'api/connection-status')
        if success:
            try:
                data = response.json()
                return self.log_test("Connection Status",
                                     'has_internet' in data,
                                     f"- Internet: {data.get('has_internet', False)}")
            except:
                return self.log_test("Connection Status", False, "- Invalid JSON response")
        return self.log_test("Connection Status", False, f"- {log_error(response)}")

    # ---------------- Notes API ----------------
    def test_create_note(self):
        test_note = {"title": "Test Note", "content": "Verifying note creation."}
        success, response = self.run_request('POST', 'api/notes', data=test_note, expected_status=200)
        if success:
            try:
                data = response.json()
                if 'id' in data:
                    self.created_resources['notes'].append(data['id'])
                    return self.log_test("Create Note", True, f"- ID: {data.get('id')[:8]}...")
            except:
                return self.log_test("Create Note", False, "- Invalid JSON response")
        return self.log_test("Create Note", False, f"- {log_error(response)}")

    def test_get_notes(self):
        success, response = self.run_request('GET', 'api/notes')
        if success:
            try:
                data = response.json()
                return self.log_test("Get All Notes", isinstance(data, list), f"- Found {len(data)} notes")
            except:
                return self.log_test("Get All Notes", False, "- Invalid JSON response")
        return self.log_test("Get All Notes", False, f"- {log_error(response)}")

    def test_get_specific_note(self):
        if not self.created_resources['notes']:
            return self.log_test("Get Specific Note", False, "- No notes created")
        note_id = self.created_resources['notes'][0]
        success, response = self.run_request('GET', f'api/notes/{note_id}')
        if success:
            try:
                data = response.json()
                return self.log_test("Get Specific Note", data.get('id') == note_id,
                                     f"- Title: {data.get('title', 'N/A')}")
            except:
                return self.log_test("Get Specific Note", False, "- Invalid JSON response")
        return self.log_test("Get Specific Note", False, f"- {log_error(response)}")

    # ---------------- Schedule API ----------------
    def test_create_schedule(self):
        future_time = datetime.utcnow() + timedelta(hours=1)
        test_schedule = {
            "title": "Test Reminder",
            "description": "This is a test reminder",
            "scheduled_time": future_time.isoformat(),
            "notification_type": "reminder"
        }
        success, response = self.run_request('POST', 'api/schedule', data=test_schedule, expected_status=200)
        if success:
            try:
                data = response.json()
                if 'id' in data:
                    self.created_resources['schedules'].append(data['id'])
                    return self.log_test("Create Schedule", True, f"- ID: {data.get('id')[:8]}...")
            except:
                return self.log_test("Create Schedule", False, "- Invalid JSON response")
        return self.log_test("Create Schedule", False, f"- {log_error(response)}")

    def test_get_schedules(self):
        success, response = self.run_request('GET', 'api/schedule')
        if success:
            try:
                data = response.json()
                return self.log_test("Get All Schedules", isinstance(data, list), f"- Found {len(data)} schedules")
            except:
                return self.log_test("Get All Schedules", False, "- Invalid JSON response")
        return self.log_test("Get All Schedules", False, f"- {log_error(response)}")

    def test_get_upcoming_schedules(self):
        success, response = self.run_request('GET', 'api/schedule/upcoming')
        if success:
            try:
                data = response.json()
                return self.log_test("Get Upcoming Schedules", isinstance(data, list), f"- Found {len(data)} upcoming")
            except:
                return self.log_test("Get Upcoming Schedules", False, "- Invalid JSON response")
        return self.log_test("Get Upcoming Schedules", False, f"- {log_error(response)}")

    def test_complete_schedule(self):
        if not self.created_resources['schedules']:
            return self.log_test("Complete Schedule", False, "- No schedules created")
        schedule_id = self.created_resources['schedules'][0]
        success, response = self.run_request('PUT', f'api/schedule/{schedule_id}/complete', expected_status=200)
        if success:
            try:
                data = response.json()
                return self.log_test("Complete Schedule", 'message' in data, f"- {data.get('message', 'Completed')}")
            except:
                return self.log_test("Complete Schedule", False, "- Invalid JSON response")
        return self.log_test("Complete Schedule", False, f"- {log_error(response)}")

    # ---------------- Summaries & PDF ----------------
    def test_pdf_upload(self):
        test_pdf_path = os.path.join(os.path.dirname(__file__), "test_document.pdf")
        if not os.path.exists(test_pdf_path):
            return self.log_test("PDF Upload", False, "- Test PDF not found")
        try:
            with open(test_pdf_path, 'rb') as f:
                files = {'file': ('test_document.pdf', f, 'application/pdf')}
                success, response = self.run_request('POST', 'api/upload-pdf', files=files, expected_status=200)
            if success:
                try:
                    data = response.json()
                    if 'id' in data:
                        self.created_resources['summaries'].append(data['id'])
                        return self.log_test("PDF Upload", True, f"- File: {data.get('filename', 'N/A')}")
                except Exception as e:
                    return self.log_test("PDF Upload", False, f"- JSON error: {str(e)}")
            else:
                return self.log_test("PDF Upload", False, f"- {log_error(response)}")
        except Exception as e:
            return self.log_test("PDF Upload", False, f"- File error: {str(e)}")

    def test_get_summaries(self):
        success, response = self.run_request('GET', 'api/summaries')
        if success:
            try:
                data = response.json()
                return self.log_test("Get All Summaries", isinstance(data, list), f"- Found {len(data)} summaries")
            except:
                return self.log_test("Get All Summaries", False, "- Invalid JSON response")
        return self.log_test("Get All Summaries", False, f"- {log_error(response)}")

    def test_refresh_summary(self):
        if not self.created_resources['summaries']:
            return self.log_test("Refresh Summary", False, "- No summaries created")
        summary_id = self.created_resources['summaries'][0]
        success, response = self.run_request('POST', f'api/refresh-summary/{summary_id}', expected_status=200)
        if success:
            try:
                data = response.json()
                success_condition = 'updated' in data or 'summary' in data
                return self.log_test("Refresh Summary", success_condition, f"- Keys: {list(data.keys())}")
            except:
                return self.log_test("Refresh Summary", False, "- Invalid JSON response")
        return self.log_test("Refresh Summary", False, f"- {log_error(response)}")

    # ---------------- Copilot Command ----------------
    def test_copilot_command(self):
        command = get_random_command()
        success, response = self.run_request('POST', 'api/copilot/process-command', data=command, expected_status=200)
        if success:
            try:
                data = response.json()
                return self.log_test("Copilot Command", 'response' in data, f"- Reply: {data.get('response', 'N/A')}")
            except:
                return self.log_test("Copilot Command", False, "- Invalid JSON response")
        return self.log_test("Copilot Command", False, f"- {log_error(response)}")

    # ---------------- Run All ----------------
    def run_all_tests(self):
        print("🚀 Starting Comprehensive Backend API Testing")
        print("=" * 60)

        print("\n📡 CONNECTIVITY TESTS")
        self.test_connection_status()

        print("\n📝 NOTES API TESTS")
        self.test_create_note()
        self.test_get_notes()
        self.test_get_specific_note()

        print("\n⏰ SCHEDULE API TESTS")
        self.test_create_schedule()
        self.test_get_schedules()
        self.test_get_upcoming_schedules()
        self.test_complete_schedule()

        print("\n📄 PDF & SUMMARY TESTS")
        self.test_pdf_upload()
        self.test_get_summaries()
        self.test_refresh_summary()

        print("\n🤖 COPILOT TESTS")
        self.test_copilot_command()

        print("\n" + "=" * 60)
        print(f"📊 FINAL RESULTS: {self.tests_passed}/{self.tests_run} tests passed")

        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED! Backend API is working correctly.")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed. Check the issues above.")
            return 1


def main():
    tester = ResourceAppAPITester()
    return tester.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
