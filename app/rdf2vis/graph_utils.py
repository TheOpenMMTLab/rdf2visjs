import re
import base64
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from rdflib import Graph
from .sparql_wrapper import SparQLWrapper
from .mapping_reader import MappingReader


def _is_http_url(source):
    return source.startswith("http://") or source.startswith("https://")


def _download_rdf(url, source_auth=None):
    headers = {
        "Accept": "text/turtle, application/x-turtle, application/ld+json;q=0.9, */*;q=0.1"
    }
    if source_auth:
        auth_type = source_auth.get("type", "").lower()
        if auth_type == "bearer" and source_auth.get("token"):
            headers["Authorization"] = f"Bearer {source_auth['token']}"
        elif auth_type == "basic" and source_auth.get("username") is not None and source_auth.get("password") is not None:
            raw = f"{source_auth['username']}:{source_auth['password']}".encode("utf-8")
            headers["Authorization"] = f"Basic {base64.b64encode(raw).decode('ascii')}"
    print(f"Downloading RDF from {url} with headers: {headers} source_auth: {source_auth}")
    req = Request(url, headers=headers)
    try:
        with urlopen(req) as response:
            status_code = response.getcode()
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            payload = response.read().decode("utf-8", errors="replace")

            if status_code < 200 or status_code >= 300:
                raise RuntimeError(f"RDF-Download fehlgeschlagen: HTTP {status_code} ({final_url})")

            is_html = "text/html" in content_type.lower() or payload.lstrip().lower().startswith(("<!doctype html", "<html"))
            if is_html:
                preview = payload[:300].replace("\n", " ")
                raise RuntimeError(
                    "RDF-Download liefert HTML statt Turtle/JSON-LD. "
                    f"Status={status_code}, URL={final_url}, Content-Type={content_type}, Body-Preview={preview}"
                )

            return payload
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        preview = body[:300].replace("\n", " ")
        raise RuntimeError(f"RDF-Download fehlgeschlagen: HTTP {exc.code} für {url}. Body-Preview={preview}") from exc
    except URLError as exc:
        raise RuntimeError(f"RDF-Download fehlgeschlagen: Netzwerkfehler für {url}: {exc.reason}") from exc


def gen_graph(filename, mapping_yaml_file, source_auth=None):

    # RDF-Graph erzeugen
    g = Graph()

    # Datei im Turtle-Format einlesen
    if _is_http_url(filename):
        rdf_text = _download_rdf(filename, source_auth=source_auth)
        print(f"Downloaded RDF data from {filename}:\n{rdf_text}...\n")
        g.parse(data=rdf_text, format="turtle")
    else:
        g.parse(filename, format="turtle")

    # Anzahl der Tripel anzeigen
    print(f"Graph hat {len(g)} Tripel.\n")

    nodes = []
    nodes_id = dict()
    node_id = 0

    # Mapping-Datei einlesen
    mapping_reader = MappingReader(mapping_yaml_file)
    views = mapping_reader.get_views()

    instance_types = set()
    sparql_wrapper = SparQLWrapper(g)
    for inst in sparql_wrapper.get_instances():

        user_data = {
            "type": "None",
            "label": "-"
        }
        attributes = {}
        # Instanztyp abfragen
        inst_type = str(sparql_wrapper.get_type(inst))
        instance_types.add(inst_type)

        icon = mapping_reader.get_icon_for_uri(inst_type, "/icons/node-svgrepo-com.svg")
        print(inst, "type:", inst_type, icon)

        user_data["type"] = inst_type.split("#")[-1]  # Nur den letzten Teil des Typs verwenden
        label = str(inst)
        for prop, obj in sparql_wrapper.get_object_properties(inst):
            print(inst, "property:", prop, "object:", obj)
            key = prop.split("#")[-1]  # Nur den letzten Teil des Properties verwenden
            if key == "name" or key == "label":
                label = str(obj)
            elif key == "comment":
                user_data["comment"] = str(obj)
            elif key == "type":
                # ignore type property
                continue
            else:
                attributes[key] = str(obj)

        if attributes:
            user_data["attributes"] = attributes
        user_data["label"] = label

        if "{{label}}" in icon:
            # Platzhalter im Icon ersetzen und Label löschen
            print("Replacing label in icon:", icon)
            icon = icon.replace("{{label}}", label)
            label = ""

        node_id += 1
        nodes_id[inst] = node_id

        # Views
        user_data["views"] = []
        for view in views:
            if mapping_reader.contains_in_view(view, inst_type):
                user_data["views"].append(view)

        nodes.append({"id": node_id, "label": label, "shape": "image", "image": icon, "user_data": user_data})

    edges = []
    for from_ref, ref, to_ref in sparql_wrapper.get_references():
        print(from_ref, ref, to_ref)

        label = re.split(r'[/#](?=[^/#]*$)', str(ref))[-1]

        edges.append({"from": nodes_id[from_ref], "to": nodes_id[to_ref], "label": label})

    it = sorted(list(instance_types))
    print("Instance types:", it)

    view_lables = {}
    for view in views:
        view_lables[view] = mapping_reader.get_view_config(view)["name"]

    return {
        "views": view_lables,
        "nodes": nodes,
        "edges": edges
    }
