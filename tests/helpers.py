from datetime import date


def create_user_and_token(client, username, email, password):
    client.post("/users/sign-up", json={
        "username": username,
        "email": email,
        "password": password,
    })

    res = client.post("/users/sign-in", data={
        "username": email,
        "password": password,
    })
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_budget(client, headers, category="Food", monthly_limit=1000):
    return client.post("/budgets/", json={
        "category": category,
        "monthly_limit": monthly_limit,
    }, headers=headers)


def create_expense(client, headers, title="Lunch", amount=10, category="Food", description="test"):
    return client.post("/expenses/", json={
        "title": title,
        "amount": amount,
        "category": category,
        "description": description,
        "date": date.today().isoformat(),
    }, headers=headers)
