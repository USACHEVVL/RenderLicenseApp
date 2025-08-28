from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import datetime
import uuid
from server.db.session import SessionLocal
from server.models.license import License
from server.models.user import User
from starlette.status import HTTP_303_SEE_OTHER
from sqlalchemy import or_, cast, String

admin_router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@admin_router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, status: str = "", sort: str = "", q: str = ""):
    db = SessionLocal()
    now = datetime.datetime.now()

    # Присоединяем таблицы
    licenses_query = db.query(License).join(User)

    # --- ПОИСК ---
    if q:
        licenses_query = licenses_query.filter(
            or_(
                License.license_key.ilike(f"%{q}%"),
                cast(User.telegram_id, String).ilike(f"%{q}%")
            )
        )

    # --- ФИЛЬТР ПО СТАТУСУ ---
    if status == "active":
        licenses_query = licenses_query.filter(License.is_active == True)
    elif status == "inactive":
        licenses_query = licenses_query.filter(License.is_active == False)

    # --- СОРТИРОВКА ---
    if sort == "next_charge_at_asc":
        licenses_query = licenses_query.order_by(License.next_charge_at.asc())
    elif sort == "next_charge_at_desc":
        licenses_query = licenses_query.order_by(License.next_charge_at.desc())

    licenses = licenses_query.all()

    enriched_licenses = []
    for lic in licenses:
        user = db.query(User).filter_by(id=lic.user_id).first()

        enriched_licenses.append({
            "key": lic.license_key,
            "next_charge_at": lic.next_charge_at.strftime("%d.%m.%Y") if lic.next_charge_at else "—",
            "user_id": user.telegram_id if user else "—",
            "status": "✅ Активна" if lic.is_active else "❌ Неактивна"
        })

    db.close()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "licenses": enriched_licenses,
        "selected_status": status,
        "selected_sort": sort,
        "q": q
    })

@admin_router.post("/admin/delete")
def delete_license(license_key: str = Form(...)):
    db = SessionLocal()
    try:
        license = db.query(License).filter_by(license_key=license_key).first()
        if license:
            db.delete(license)
            db.commit()
    finally:
        db.close()

    return RedirectResponse(url="/admin", status_code=303)


@admin_router.post("/admin/reduce")
def reduce_license(license_key: str = Form(...)):
    """Reduce the validity of a license by 30 days."""
    db = SessionLocal()
    try:
        license = db.query(License).filter_by(license_key=license_key).first()
        if license and license.next_charge_at:
            license.next_charge_at -= datetime.timedelta(days=30)
            license.valid_until = license.next_charge_at
            db.commit()
    finally:
        db.close()

    return RedirectResponse(url="/admin", status_code=303)


@admin_router.post("/admin/extend")
def extend_license(license_key: str = Form(...)):
    """Extend the validity of a license by 30 days."""
    db = SessionLocal()
    try:
        license = db.query(License).filter_by(license_key=license_key).first()
        if license:
            base = license.next_charge_at or datetime.datetime.now()
            license.next_charge_at = base + datetime.timedelta(days=30)
            license.valid_until = license.next_charge_at
            license.is_active = True
            db.commit()
    finally:
        db.close()

    return RedirectResponse(url="/admin", status_code=303)

@admin_router.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request):
    db = SessionLocal()
    users = db.query(User).all()
    user_data = []

    for u in users:
        license_count = db.query(License).filter_by(user_id=u.id).count()

        user_data.append({
            "id": u.id,
            "telegram_id": u.telegram_id,
            "license_count": license_count,
        })

    db.close()

    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": user_data
    })

@admin_router.post("/admin/users/delete")
def delete_user(user_id: int = Form(...)):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if user:
            db.delete(user)
            db.commit()
    finally:
        db.close()

    return RedirectResponse(url="/admin/users", status_code=HTTP_303_SEE_OTHER)


@admin_router.post("/admin/create")
def create_license(telegram_id: int = Form(...), days: int = Form(...)):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            # Если пользователь не найден, можно создать его
            user = User(telegram_id=telegram_id)
            db.add(user)
            db.commit()
            db.refresh(user)

        license_key = str(uuid.uuid4())
        next_charge_at = datetime.datetime.now() + datetime.timedelta(days=days)

        existing = db.query(License).filter_by(user_id=user.id).first()
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
                user_id=user.id
            )
            db.add(new_license)

        db.commit()

    finally:
        db.close()

    return RedirectResponse(url="/admin", status_code=303)
