from redis.asyncio import Redis

EMAIL_COOLDOWN_SECONDS = 60
IP_WINDOW_SECONDS = 10 * 60
IP_MAX_REQUESTS = 10


class RateLimitError(Exception):
    pass


async def acquire_verification_send_quota(redis: Redis, email: str, ip: str) -> None:
    email_key = f"verify:limit:email:{email}"
    ip_key = f"verify:limit:ip:{ip}"

    ip_count = int(await redis.get(ip_key) or 0)
    if ip_count >= IP_MAX_REQUESTS:
        raise RateLimitError

    acquired = await redis.set(email_key, "1", nx=True, ex=EMAIL_COOLDOWN_SECONDS)
    if not acquired:
        raise RateLimitError

    count = await redis.incr(ip_key)
    if count == 1:
        await redis.expire(ip_key, IP_WINDOW_SECONDS)
    if count > IP_MAX_REQUESTS:
        await redis.delete(email_key)
        raise RateLimitError
