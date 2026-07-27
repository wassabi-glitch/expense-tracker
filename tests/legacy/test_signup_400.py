import urllib.request
import urllib.error
import json

data = json.dumps({
    "email": "testmobile@example.com",
    "username": "testmobile123",
    "password": "StrongPassword123!"
}).encode('utf-8')

req = urllib.request.Request(
    "http://127.0.0.1:9000/users/sign-up",
    method="POST",
    headers={
        "Content-Type": "application/json",
        "Host": "192.168.1.16:9000"
    },
    data=data
)

try:
    with urllib.request.urlopen(req) as response:
        print("STATUS:", response.status)
        print("BODY:", response.read().decode())
except urllib.error.HTTPError as e:
    print("STATUS:", e.code)
    print("BODY:", e.read().decode())
