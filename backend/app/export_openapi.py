"""Export OpenAPI JSON specification from FastAPI application."""

import json
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import create_app  # noqa: E402


def export_openapi(output_path: Path | None = None) -> dict:
    """Generate and save OpenAPI specification to JSON."""
    if output_path is None:
        # Default to frontend/openapi.json relative to repository root
        root_dir = Path(__file__).resolve().parent.parent.parent
        output_path = root_dir / "frontend" / "openapi.json"

    app = create_app()
    openapi_schema = app.openapi()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)

    print(f"Exported OpenAPI spec to {output_path} ({len(openapi_schema.get('paths', {}))} paths, {len(openapi_schema.get('components', {}).get('schemas', {}))} schemas)")
    return openapi_schema


if __name__ == "__main__":
    export_openapi()
