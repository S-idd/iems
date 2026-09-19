#!/usr/bin/env python3
"""Generate the executable IEMS Postman collection from its API workflow."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
groups = {}


def add(group, name, method, path, role=None, body=None, status=200, checks=(), save=None, before=None, description=None):
    headers = []
    if role:
        headers.append({"key": "Authorization", "value": f"Bearer {{{{{role}Token}}}}"})
    if body is not None:
        headers.append({"key": "Content-Type", "value": "application/json"})
    request = {"method": method, "header": headers, "url": "{{baseUrl}}" + path,
               "description": description or f"{method} {path}. Run the collection in order so earlier requests provide the required IDs and tokens."}
    if body is not None:
        request["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2), "options": {"raw": {"language": "json"}}}
    script = [f"pm.test('HTTP {status}', () => pm.response.to.have.status({status}));"]
    if checks or save:
        script.append("const result = pm.response.json();")
    for check in checks:
        script.append(f"pm.test({json.dumps(check)}, () => pm.expect({check}).to.be.true);")
    if save:
        script.append(f"pm.collectionVariables.set('{save[0]}', String({save[1]}));")
    events = [{"listen": "test", "script": {"type": "text/javascript", "exec": script}}]
    if before:
        events.insert(0, {"listen": "prerequest", "script": {"type": "text/javascript", "exec": before}})
    items = groups.setdefault(group, [])
    items.append({"name": f"{len(items) + 1:02d} {name}", "event": events, "request": request})


add("Authentication", "Login demo admin", "POST", "/api/auth/login", body={"username": "demo-admin", "password": "{{adminPassword}}"}, checks=["!!result.accessToken", "result.user.role === 'ADMIN'"], save=("adminToken", "result.accessToken"), before=["if (!pm.variables.get('adminPassword')) throw new Error('Set adminPassword in the IEMS Demo environment before running.');", "['adminToken','studentToken','studentRefreshToken','schoolId','studentUserId','studentId','scholarshipId','rejectId','cancelId','reportId','notificationId'].forEach(key => pm.collectionVariables.unset(key));", "pm.collectionVariables.set('runId', Date.now().toString(36) + Math.random().toString(36).slice(2, 6));", "pm.collectionVariables.set('userPassword', 'Demo-' + pm.collectionVariables.get('runId') + '-Pass!');"], description="Start here. Logs in with the local demo-admin account, clears IDs from a previous run, and creates a unique run ID. Set adminPassword in the environment before running.")

school = {"name": "Postman School {{runId}}", "code": "P{{runId}}", "city": "Bengaluru", "state": "Karnataka", "district": "Bengaluru Urban", "active": True}
add("Schools", "Create school", "POST", "/api/schools", "admin", school, checks=["!!result.data.id", "result.data.name.includes('Postman School')"], save=("schoolId", "result.data.id"))
for name, path, expr in [
    ("List active", "/active", "result.data.some(x => String(x.id) === pm.collectionVariables.get('schoolId'))"),
    ("List paged", "?page=0&size=20", "Array.isArray(result.data.content)"),
    ("Get by ID", "/{{schoolId}}", "String(result.data.id) === pm.collectionVariables.get('schoolId')"),
    ("Get by city", "/city/bengaluru", "result.data.some(x => String(x.id) === pm.collectionVariables.get('schoolId'))"),
    ("Get by state", "/state/karnataka", "result.data.some(x => String(x.id) === pm.collectionVariables.get('schoolId'))"),
    ("Get by district", "/district/bengaluru%20urban", "result.data.some(x => String(x.id) === pm.collectionVariables.get('schoolId'))"),
    ("Search", "/search?keyword=Postman", "result.data.some(x => String(x.id) === pm.collectionVariables.get('schoolId'))"),
    ("Get by code", "/code/P{{runId}}", "String(result.data.id) === pm.collectionVariables.get('schoolId')"),
]:
    add("Schools", name, "GET", "/api/schools" + path, "admin", checks=[expr])
add("Schools", "Update school", "PUT", "/api/schools/{{schoolId}}", "admin", {**school, "name": "Updated Postman School {{runId}}"}, checks=["result.data.name.includes('Updated Postman')"])

add("Student authentication", "Register student user", "POST", "/api/auth/register", "admin", {"username": "student{{runId}}", "password": "{{userPassword}}", "email": "student{{runId}}@example.test", "role": "STUDENT", "firstName": "Demo", "lastName": "Student", "schoolId": "{{schoolId}}"}, checks=["result.role === 'STUDENT'", "!!result.id"], save=("studentUserId", "result.id"))
add("Student authentication", "Login student", "POST", "/api/auth/login", body={"username": "student{{runId}}", "password": "{{userPassword}}"}, checks=["!!result.accessToken", "!!result.refreshToken"], save=("studentToken", "result.accessToken"))
groups["Student authentication"][-1]["event"][-1]["script"]["exec"].append("pm.collectionVariables.set('studentRefreshToken', result.refreshToken);")
add("Student authentication", "Refresh student token", "POST", "/api/auth/refresh-token?refreshToken={{studentRefreshToken}}", checks=["!!result.accessToken"], save=("studentToken", "result.accessToken"))

student = {"userId": "{{studentUserId}}", "studentNumber": "N{{runId}}", "hasDisability": True, "disabilities": ["VISUAL"], "currentYear": 2, "gpa": 3.5}
add("Students", "Create student profile", "POST", "/api/students", "admin", student, checks=["!!result.data.id"], save=("studentId", "result.data.id"))
for name, path, expr in [
    ("List paged", "?page=0&size=20", "Array.isArray(result.data.content)"),
    ("Get by ID", "/{{studentId}}", "String(result.data.id) === pm.collectionVariables.get('studentId')"),
    ("Get by user", "/user/{{studentUserId}}", "String(result.data.id) === pm.collectionVariables.get('studentId')"),
    ("Get by number", "/number/N{{runId}}", "String(result.data.id) === pm.collectionVariables.get('studentId')"),
    ("Get by school", "/school/{{schoolId}}", "result.data.some(x => String(x.id) === pm.collectionVariables.get('studentId'))"),
    ("Get disabilities", "/disabilities", "result.data.some(x => String(x.id) === pm.collectionVariables.get('studentId'))"),
    ("School statistics", "/statistics/{{schoolId}}", "result.data.totalStudents >= 1"),
]:
    add("Students", name, "GET", "/api/students" + path, "admin", checks=[expr])
add("Students", "Update student", "PUT", "/api/students/{{studentId}}", "admin", {"accommodationsNeeded": "Large print", "gpa": 3.7}, checks=["result.data.accommodationsNeeded === 'Large print'"])

application = {"scholarshipName": "Access Fund", "studentId": "{{studentId}}", "amountRequested": 1000, "purpose": "Assistive equipment"}
add("Scholarships", "Apply", "POST", "/api/scholarships", "student", application, checks=["result.status === 'PENDING'"], save=("scholarshipId", "result.id"))
add("Scholarships", "Update pending", "PUT", "/api/scholarships/{{scholarshipId}}", "student", {**application, "amountRequested": 1200}, checks=["result.amountRequested === 1200"])
for name, path, expr in [
    ("List paged", "?page=0&size=20", "Array.isArray(result.content)"),
    ("Get by ID", "/{{scholarshipId}}", "String(result.id) === pm.collectionVariables.get('scholarshipId')"),
    ("Get by student", "/student/{{studentId}}", "result.some(x => String(x.id) === pm.collectionVariables.get('scholarshipId'))"),
    ("Get by status", "/status/PENDING", "result.some(x => String(x.id) === pm.collectionVariables.get('scholarshipId'))"),
    ("Get by status paged", "/status/PENDING/paged?page=0&size=20", "Array.isArray(result.content)"),
    ("Statistics", "/stats", "result.totalApplications >= 1"),
]:
    add("Scholarships", name, "GET", "/api/scholarships" + path, "admin", checks=[expr])
add("Scholarships", "Average processing time", "GET", "/api/scholarships/avg-processing-time", "admin")
add("Scholarships", "Approve", "PUT", "/api/scholarships/{{scholarshipId}}/approve?approvedAmount=1000&comments=Approved", "admin", checks=["result.status === 'APPROVED'"])
add("Scholarships", "Disburse", "PUT", "/api/scholarships/{{scholarshipId}}/disburse?reference=POSTMAN-{{runId}}", "admin", checks=["result.status === 'DISBURSED'"])
for action in ("reject", "cancel"):
    add("Scholarships", f"Apply for {action}", "POST", "/api/scholarships", "student", {**application, "scholarshipName": f"{action.title()} Fund"}, checks=["result.status === 'PENDING'"], save=(f"{action}Id", "result.id"))
    if action == "reject":
        add("Scholarships", "Reject", "PUT", "/api/scholarships/{{rejectId}}/reject?comments=Not%20eligible", "admin", checks=["result.status === 'REJECTED'"])
    else:
        add("Scholarships", "Cancel", "DELETE", "/api/scholarships/{{cancelId}}/cancel", "student", status=204)

report = {"studentId": "{{studentId}}", "schoolId": "{{schoolId}}", "title": "Ramp review", "description": "Review entrance access", "relatedDisability": "VISUAL"}
add("Accessibility", "Create report", "POST", "/api/accessibility", "admin", report, checks=["!!result.id"], save=("reportId", "result.id"))
add("Accessibility", "List paged", "GET", "/api/accessibility?page=0&size=20", "admin", checks=["Array.isArray(result.content)"])
add("Accessibility", "Get report", "GET", "/api/accessibility/{{reportId}}", "admin", checks=["String(result.id) === pm.collectionVariables.get('reportId')"])
add("Accessibility", "Update report", "PUT", "/api/accessibility/{{reportId}}", "admin", {**report, "title": "Updated ramp review"}, checks=["result.title === 'Updated ramp review'"])
add("Accessibility", "Delete report", "DELETE", "/api/accessibility/{{reportId}}", "admin", status=204)

add("Notifications", "List notifications", "GET", "/api/notifications", "admin", checks=["Array.isArray(result)", "result.length >= 1"], save=("notificationId", "result[0].id"))
add("Notifications", "List unread", "GET", "/api/notifications/unread", "admin", checks=["Array.isArray(result)"])
add("Notifications", "Count unread", "GET", "/api/notifications/unread/count", "admin", checks=["typeof result === 'number'", "result >= 1"])
add("Notifications", "Student cannot read admin notification", "PUT", "/api/notifications/{{notificationId}}/read", "student", status=404)
add("Notifications", "Student cannot delete admin notification", "DELETE", "/api/notifications/{{notificationId}}", "student", status=404)
add("Notifications", "Mark one read", "PUT", "/api/notifications/{{notificationId}}/read", "admin", status=204)
add("Notifications", "Mark all read", "PUT", "/api/notifications/mark-all-read", "admin", status=204)
add("Notifications", "Verify unread count is zero", "GET", "/api/notifications/unread/count", "admin", checks=["result === 0"])
add("Notifications", "Delete notification", "DELETE", "/api/notifications/{{notificationId}}", "admin", status=204)

add("Cleanup", "Delete student", "DELETE", "/api/students/{{studentId}}", "admin", checks=["result.success === true"])
add("Cleanup", "Delete school", "DELETE", "/api/schools/{{schoolId}}", "admin", checks=["result.success === true"])
add("Cleanup", "Logout student", "POST", "/api/auth/logout", "student", status=204)

collection = {
    "info": {"name": "IEMS API | Live Demo", "description": "Run the whole collection in order against a disposable IEMS database. Import the IEMS Demo environment, set adminPassword, start the local API, and seed one demo notification as described in postman/README.md. Requests create their own school, student and scholarship records, then demonstrate search, state transitions, access control and cleanup. Every IEMS controller route is covered. DCG checks are a separate demo.", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
    "variable": [{"key": "baseUrl", "value": "http://127.0.0.1:8090"}],
    "item": [
        {"name": "Authentication", "description": "Start here: log in as demo-admin and initialize a fresh run.", "item": groups["Authentication"]},
        {"name": "Schools", "description": "Create a school and demonstrate listing, lookup, filters, search and update.", "item": groups["Schools"]},
        {"name": "Students", "description": "Register and authenticate a student, refresh the token, then demonstrate student profile endpoints.", "item": [
            {"name": "Student sign-in", "description": "These requests need the school created in the previous folder.", "item": groups["Student authentication"]},
            *groups["Students"],
        ]},
        {"name": "Scholarships", "description": "Apply, edit, query, approve, disburse, reject and cancel applications with role-specific tokens.", "item": groups["Scholarships"]},
        {"name": "Accessibility Reports", "description": "Create, list, retrieve, update and delete an accessibility report.", "item": groups["Accessibility"]},
        {"name": "Notifications", "description": "Requires a seeded demo-admin notification. Demonstrates inbox, unread count, ownership checks, mark read and delete.", "item": groups["Notifications"]},
        {"name": "Demo cleanup", "description": "Run last: delete the student profile, deactivate the school and log out.", "item": groups["Cleanup"]},
    ],
}
target = ROOT / "postman" / "iems-api-collection.json"
target.write_text(json.dumps(collection, indent=2) + "\n")
print(f"Wrote {sum(map(len, groups.values()))} requests to {target}")
