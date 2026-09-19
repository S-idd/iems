#!/usr/bin/env python3
"""Exercise a running, local IEMS API without printing JWTs or passwords."""
import json
import os
import secrets
import time
import urllib.error
import sys
import urllib.request


def smoke(base):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for attempt in range(60):
        try:
            with opener.open(base + '/actuator/health', timeout=1) as response:
                if response.status == 200:
                    break
        except (OSError, urllib.error.URLError):
            time.sleep(0.5)
    else:
        raise RuntimeError('IEMS did not become healthy within 30 seconds')
    token = None
    def request(method, path, body=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        data = None if body is None else json.dumps(body).encode()
        with opener.open(urllib.request.Request(base + path, data, headers, method=method), timeout=15) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    token = request("POST", "/api/auth/login", {"username": "demo-admin",
                    "password": os.environ["IEMS_DEMO_ADMIN_PASSWORD"]})["accessToken"]
    suffix = secrets.token_hex(5)
    password = secrets.token_urlsafe(24)
    user = 'demo' + suffix
    request('POST', '/api/auth/register', {'username': user, 'password': password,
            'email': user + '@example.test', 'role': 'ADMIN', 'firstName': 'Demo', 'lastName': 'Admin'})
    token = request('POST', '/api/auth/login', {'username': user, 'password': password})['accessToken']
    code = 'S' + suffix.upper()
    school = request('POST', '/api/schools', {'name': 'Portable Demo ' + suffix, 'code': code,
                     'city': 'Bengaluru', 'state': 'Karnataka', 'district': 'Bengaluru Urban'})['data']
    assert request('GET', '/api/schools/code/' + code.lower())['data']['id'] == school['id']
    assert any(s['id'] == school['id'] for s in request('GET', '/api/schools/city/bengaluru')['data'])
    request('PUT', '/api/schools/' + str(school['id']), {'name': 'Updated Demo ' + suffix,
            'code': code, 'district': 'Updated District'})
    assert request('GET', '/api/schools/code/' + code)['data']['district'] == 'Updated District'
    admin_token = token
    student_user = request('POST', '/api/auth/register', {
        'username': 'student' + suffix, 'password': password,
        'email': 'student' + suffix + '@example.test', 'role': 'STUDENT',
        'firstName': 'Demo', 'lastName': 'Student', 'schoolId': school['id']})
    student = request('POST', '/api/students', {
        'userId': student_user['id'], 'studentNumber': 'N' + suffix,
        'hasDisability': True, 'disabilities': ['VISUAL']})['data']
    assert request('GET', '/api/students/' + str(student['id']))['data']['id'] == student['id']
    token = request('POST', '/api/auth/login', {'username': 'student' + suffix,
                                              'password': password})['accessToken']
    scholarship = request('POST', '/api/scholarships', {
        'scholarshipName': 'Access Fund', 'studentId': student['id'],
        'amountRequested': 1000})
    assert request('GET', '/api/scholarships/' + str(scholarship['id']))['studentId'] == student['id']
    token = admin_token
    report = request('POST', '/api/accessibility', {
        'schoolId': school['id'], 'studentId': student['id'],
        'title': 'Ramp review', 'description': 'Review entrance access',
        'relatedDisability': 'VISUAL'})
    assert request('GET', '/api/accessibility/' + str(report['id']))['schoolId'] == school['id']
    request('GET', '/api/scholarships/avg-processing-time')
    request('DELETE' , '/api/schools/' + str(school['id']))
    print('PASS: JWT, school, student, scholarship and accessibility API flows')


if __name__ == '__main__':
    smoke(sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8090')
