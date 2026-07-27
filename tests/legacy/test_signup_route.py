import urllib.request
import urllib.error

req = urllib.request.Request("http://127.0.0.1:9000/users/sign-up", method="POST", headers={"Content-Type": "application/json"}, data=b"{}")
try:
    with urllib.request.urlopen(req) as response:
        print("STATUS:", response.status)
        print("BODY:", response.read().decode())
except urllib.error.HTTPError as e:
    print("STATUS:", e.code)
    print("BODY:", e.read().decode())
