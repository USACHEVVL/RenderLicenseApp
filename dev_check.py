"""Simple debug script to inspect users and licenses asynchronously."""

import asyncio
from sqlalchemy import select

from server.db.session import SessionLocal
from server.models.license import License
from server.models.user import User


async def main() -> None:
    async with SessionLocal() as db:
        users = (await db.execute(select(User))).scalars().all()
        licenses = (await db.execute(select(License))).scalars().all()

        print(f"Users: {users}")
        print(f"Licenses: {licenses}")


if __name__ == "__main__":
    asyncio.run(main())
