from server.db.base_class import Base

# Импорт моделей, чтобы Alembic видел их
from server.models.user import User
from server.models.license import License
from server.models.machine import Machine
