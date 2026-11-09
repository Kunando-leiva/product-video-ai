"""Script de arranque local del backend."""
import uvicorn  # type: ignore[reportMissingImports]
from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )