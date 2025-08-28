from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import datetime
import uuid

# All datetime operations use UTC to avoid timezone-related bugs.
from server.db.session import SessionLocal
from server.models.license import License
from server.models.user import User
from starlette.status import HTTP_303_SEE_OTHER
<<<<<<< ours
from sqlalchemy import or_, cast, String, func
=======
from sqlalchemy import cast, delete, or_, select, String
>>>>>>> theirs

admin_router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@admin_router.get("/admin", response_class=HTMLResponse)
<<<<<<< ours
def admin_dashboard(request: Request, status: str = "", sort: str = "", q: str = ""):
    db = SessionLocal()
    # Current UTC time, kept for potential future use
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

    # Присоединяем таблицы и сразу выбираем связанные модели
    licenses_query = db.query(License, User).join(User)

    # --- ПОИСК ---
    if q:
        licenses_query = licenses_query.filter(
            or_(
                License.license_key.ilike(f"%{q}%"),
                cast(User.telegram_id, String).ilike(f"%{q}%")
=======
async def admin_dashboard(
    request: Request, status: str = "", sort: str = "", q: str = ""
):
    async with SessionLocal() as db:
        licenses_query = select(License, User).join(User)

        if q:
            licenses_query = licenses_query.filter(
                or_(
                    License.license_key.ilike(f"%{q}%"),
                    cast(User.telegram_id, String).ilike(f"%{q}%"),
                )
>>>>>>> theirs
            )

        if status == "active":
            licenses_query = licenses_query.filter(License.is_active.is_(True))
        elif status == "inactive":
            licenses_query = licenses_query.filter(License.is_active.is_(False))

        if sort == "next_charge_at_asc":
            licenses_query = licenses_query.order_by(License.next_charge_at.asc())
        elif sort == "next_charge_at_desc":
            licenses_query = licenses_query.order_by(License.next_charge_at.desc())

        result = await db.execute(licenses_query)
        rows = result.all()

<<<<<<< ours
    enriched_licenses = [
        {
            "key": lic.license_key,
            "next_charge_at": lic.next_charge_at.strftime("%d.%m.%Y") if lic.next_charge_at else "—",
            "user_id": user.telegram_id if user else "—",
            "status": "✅ Активна" if lic.is_active else "❌ Неактивна",
        }
        for lic, user in licenses
    ]

    db.close()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "licenses": enriched_licenses,
        "selected_status": status,
        "selected_sort": sort,
        "q": q
    })
=======
    enriched_licenses = []
    for lic, user in rows:
        enriched_licenses.append(
            {
                "key": lic.license_key,
                "next_charge_at": lic.next_charge_at.strftime("%d.%m.%Y")
                if lic.next_charge_at
                else "—",
                "user_id": user.telegram_id if user else "—",
                "status": "✅ Активна" if lic.is_active else "❌ Неактивна",
            }
        )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "licenses": enriched_licenses,
            "selected_status": status,
            "selected_sort": sort,
            "q": q,
        },
    )
>>>>>>> theirs

@admin_router.post("/admin/delete")
async def delete_license(license_key: str = Form(...)):
    async with SessionLocal() as db:
        await db.execute(delete(License).filter_by(license_key=license_key))
        await db.commit()

    return RedirectResponse(url="/admin", status_code=303)


@admin_router.post("/admin/reduce")
async def reduce_license(license_key: str = Form(...)):
    """Reduce the validity of a license by 30 days."""
    async with SessionLocal() as db:
        result = await db.execute(select(License).filter_by(license_key=license_key))
        license = result.scalars().first()
        if license and license.next_charge_at:
            license.next_charge_at -= datetime.timedelta(days=30)
            license.valid_until = license.next_charge_at
            await db.commit()

    return RedirectResponse(url="/admin", status_code=303)


@admin_router.post("/admin/extend")
async def extend_license(license_key: str = Form(...)):
    """Extend the validity of a license by 30 days."""
    async with SessionLocal() as db:
        result = await db.execute(select(License).filter_by(license_key=license_key))
        license = result.scalars().first()
        if license:
            base = (license.next_charge_at or datetime.datetime.utcnow()).replace(
                tzinfo=datetime.timezone.utc
            )
            license.next_charge_at = base + datetime.timedelta(days=30)
            license.valid_until = license.next_charge_at
            license.is_active = True
            await db.commit()

    return RedirectResponse(url="/admin", status_code=303)

@admin_router.get("/admin/users", response_class=HTMLResponse)
<<<<<<< ours
def admin_users(request: Request):
    db = SessionLocal()
    users_query = (
        db.query(User, func.count(License.id).label("license_count"))
        .outerjoin(License, User.id == License.user_id)
        .group_by(User.id)
    )
    user_data = [
        {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "license_count": license_count,
        }
        for user, license_count in users_query.all()
    ]

    db.close()
=======
async def admin_users(request: Request):
    async with SessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        user_data = []

        for u in users:
            result = await db.execute(select(License).filter_by(user_id=u.id))
            license_count = len(result.scalars().all())

            user_data.append(
                {
                    "id": u.id,
                    "telegram_id": u.telegram_id,
                    "license_count": license_count,
                }
            )
>>>>>>> theirs

    return templates.TemplateResponse(
        "users.html", {"request": request, "users": user_data}
    )

@admin_router.post("/admin/users/delete")
async def delete_user(user_id: int = Form(...)):
    async with SessionLocal() as db:
        result = await db.execute(select(User).filter_by(id=user_id))
        user = result.scalars().first()
        if user:
            await db.delete(user)
            await db.commit()

    return RedirectResponse(url="/admin/users", status_code=HTTP_303_SEE_OTHER)


@admin_router.post("/admin/create")
async def create_license(telegram_id: int = Form(...), days: int = Form(...)):
    async with SessionLocal() as db:
        result = await db.execute(select(User).filter_by(telegram_id=telegram_id))
        user = result.scalars().first()
        if not user:
            user = User(telegram_id=telegram_id)
            db.add(user)
            await db.commit()
            await db.refresh(user)

        license_key = str(uuid.uuid4())
        next_charge_at = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        ) + datetime.timedelta(days=days)

        result = await db.execute(select(License).filter_by(user_id=user.id))
        existing = result.scalars().first()
        if existing:
            existing.license_key = license_key
            existing.next_charge_at = next_charge_at
            existing.valid_until = next_charge_at
            existing.is_active = True
        else:
            new_license = License(
                license_key=license_key,
                next_charge_at=next_charge_at,
                valid_until=next_charge_at,
                is_active=True,
                user_id=user.id,
            )
            db.add(new_license)

        await db.commit()

    return RedirectResponse(url="/admin", status_code=303)
