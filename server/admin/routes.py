from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import datetime
import uuid
from server.db.session import SessionLocal
from server.models.license import License
from server.models.user import User
from server.models.machine import Machine

admin_router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@admin_router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, status: str = "", sort: str = ""):
    db = SessionLocal()
    licenses_query = db.query(License)

    # --- ФИЛЬТР ПО СТАТУСУ ---
    now = datetime.datetime.now()
    if status == "active":
        licenses_query = licenses_query.filter(License.valid_until >= now)
    elif status == "expired":
        licenses_query = licenses_query.filter(License.valid_until < now)

    # --- СОРТИРОВКА ---
    if sort == "valid_until_asc":
        licenses_query = licenses_query.order_by(License.valid_until.asc())
    elif sort == "valid_until_desc":
        licenses_query = licenses_query.order_by(License.valid_until.desc())

    licenses = licenses_query.all()

    enriched_licenses = []
    for lic in licenses:
        user = db.query(User).filter_by(id=lic.user_id).first()
        machine = db.query(Machine).filter_by(license_id=lic.id).first()

        enriched_licenses.append({
            "key": lic.license_key,
            "valid_until": lic.valid_until.strftime("%d.%m.%Y"),
            "user_id": user.telegram_id if user else "—",
            "machine": machine.name if machine else "—",
            "status": "✅ Активна" if lic.valid_until > now else "❌ Просрочена"
        })

    db.close()
    return templates.TemplateResponse("index.html", {
    "request": request,
    "licenses": enriched_licenses,
    "selected_status": status,
    "selected_sort": sort
})

@admin_router.post("/admin/delete")
def delete_license(license_key: str = Form(...)):
    db = SessionLocal()
    try:
        license = db.query(License).filter_by(license_key=license_key).first()
        if license:
            # Отвязываем от машины, если привязана
            machine = db.query(Machine).filter_by(license_id=license.id).first()
            if machine:
                machine.license_id = None
            db.delete(license)
            db.commit()
    finally:
        db.close()

    return RedirectResponse(url="/admin", status_code=303)

@admin_router.post("/admin/create")
def create_license(telegram_id: str = Form(...), days: int = Form(...)):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            # Если пользователь не найден, можно создать его
            user = User(telegram_id=telegram_id)
            db.add(user)
            db.commit()
            db.refresh(user)

        license_key = str(uuid.uuid4())[:16]  # Короткий ключ, можно заменить на другой формат
        valid_until = datetime.datetime.now() + datetime.timedelta(days=days)

        new_license = License(
            license_key=license_key,
            valid_until=valid_until,
            user_id=user.id
        )

        db.add(new_license)
        db.commit()

    finally:
        db.close()

    return RedirectResponse(url="/admin", status_code=303)
