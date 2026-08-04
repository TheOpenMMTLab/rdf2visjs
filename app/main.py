import os
from pathlib import Path

import yaml
from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from rdf2vis.graph_utils import gen_graph
from rdf2vis.svg_utils import replace_placeholder


app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
PROJECTS_CONFIG_PATH = Path(os.getenv("PROJECTS_CONFIG_PATH", str(BASE_DIR / "config" / "projects.yaml")))


def _load_projects(config_path: Path):
    if not config_path.exists():
        print(f"Projects-Konfiguration nicht gefunden: {config_path}")
        return []

    with config_path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or []

    if isinstance(loaded, dict):
        loaded = loaded.get("projects", [])

    if not isinstance(loaded, list):
        raise ValueError(f"Ungültige projects.yaml: Erwartet Liste oder Objekt mit 'projects', bekommen: {type(loaded)}")

    required_fields = {"id", "name", "model", "mapping"}
    for index, project in enumerate(loaded):
        if not isinstance(project, dict):
            raise ValueError(f"Ungültiger Projekt-Eintrag an Position {index}: {project}")
        missing = required_fields - set(project.keys())
        if missing:
            raise ValueError(f"Projekt '{project.get('id', index)}' fehlt Felder: {sorted(missing)}")

    return loaded


projects = _load_projects(PROJECTS_CONFIG_PATH)

# Jinja2 Templates
templates = Jinja2Templates(directory="templates")


# Aufruf über /svg/filename.svg?text=Neuer Text
@app.get("/svg/{filename}")
def get_svg(filename: str, request: Request):
    query_params = dict(request.query_params)
    """
    Generate SVG with replaced placeholder text.
    :param filename: Name of the SVG file to be processed.
    :param text: Text to replace the placeholder in the SVG file.
    :return: Processed SVG file as a string.
    """

    svg_string = replace_placeholder(filename, query_params)

    return Response(svg_string, media_type="image/svg+xml")


@app.get("/graph/{projectId}")
def get_graph(projectId: str):
    print(f"Generating graph for project: {projectId}")
    project = next((p for p in projects if p["id"] == projectId), None)
    if not project:
        return Response(status_code=404, content="Project not found")

    source_auth = project.get("source_auth", None)

    return gen_graph(project["model"], project["mapping"], source_auth=source_auth)


# Dynamische Index-Seite
@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "projects": projects})


# Dynamische Seite für Projektgraph
@app.get("/project/{projectId}", response_class=HTMLResponse)
async def read_graph(request: Request, projectId: str):
    print(f"Generating graph for project: {projectId}")
    project = next((p for p in projects if p["id"] == projectId), None)
    if not project:
        return Response(status_code=404, content="Project not found")
    return templates.TemplateResponse("graph.html", {
        "request": request,
        "project": project
    })


# Verzeichnis für statische Dateien
app.mount("/", StaticFiles(directory="static", html=True), name="static")
