from app.redis_rate_limiter import check_and_consume, consume_token_bucket
print('IP Bucket:', check_and_consume('forgot_password', 'testclient', window_seconds=3600, max_attempts=10))
print('Email Bucket:', consume_token_bucket('forgot_pw_email', 'recovery1@test.com', capacity=3, refill_rate_per_second=3/3600))
