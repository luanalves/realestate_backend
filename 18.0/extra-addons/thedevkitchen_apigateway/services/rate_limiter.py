from datetime import datetime, timedelta


class RateLimiter:
    _attempts = {}

    @classmethod
    def check(cls, ip, email):
        now = datetime.now()
        cutoff = now - timedelta(minutes=15)

        key = f"{ip}:{email}"
        attempts = cls._attempts.get(key, [])
        attempts = [ts for ts in attempts if ts > cutoff]

        if len(attempts) >= 5:
            return False

        attempts.append(now)
        cls._attempts[key] = attempts
        return True

    @classmethod
    def clear(cls, ip, email):
        key = f"{ip}:{email}"
        if key in cls._attempts:
            del cls._attempts[key]
