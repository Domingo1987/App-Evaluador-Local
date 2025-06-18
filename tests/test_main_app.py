import sys
from pathlib import Path
import json
import os
import builtins

# Añadir la carpeta src al path para importar main_app
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from main_app import load_json, save_json, scrap_schoology


def test_load_json_success(tmp_path):
    data = {"a": 1}
    file_path = tmp_path / "data.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    result = load_json(file_path)
    assert result == data


def test_load_json_missing(tmp_path):
    missing_file = tmp_path / "missing.json"
    assert load_json(missing_file) is None


def test_save_json_success(tmp_path):
    data = {"b": 2}
    file_path = tmp_path / "out.json"
    result = save_json(data, file_path)
    assert result is True
    with open(file_path, "r", encoding="utf-8") as f:
        content = json.load(f)
    assert content == data


def test_save_json_invalid_path(tmp_path):
    data = {"c": 3}
    # Crear archivo para usar como directorio padre inválido
    invalid_parent = tmp_path / "parent_file"
    invalid_parent.write_text("dummy")
    invalid_path = invalid_parent / "child.json"
    result = save_json(data, invalid_path)
    assert result is False


def test_scrap_schoology_basic():
    html = """
    <div class='discussion-card'>
        <span class='comment-author'>John Doe</span>
        <div class='comment-body-wrapper'>
            <p>Hello</p>
            <p>World</p>
            <a href='https://example.com/doc.txt'>doc</a>
            <a href='/user/123'>ignore</a>
        </div>
        <div class='attachments-link-summary'>https://example.com/img.png</div>
    </div>
    <div class='discussion-card'>
        <span class='comment-author'>Someone Else</span>
        <div class='comment-body-wrapper'><p>Other</p></div>
    </div>
    """
    names = ["John Doe"]
    result = scrap_schoology(html, names)
    expected = {
        "John Doe": "Hello World\nAdjuntos:\nhttps://example.com/doc.txt\nhttps://example.com/img.png"
    }
    assert result == expected


def test_scrap_schoology_ignore_nonlisted():
    html = """
    <div class='discussion-card'>
        <span class='comment-author'>Jane Doe</span>
        <div class='comment-body-wrapper'><p>Hi</p></div>
    </div>
    """
    names = ["John Doe"]
    result = scrap_schoology(html, names)
    assert result == {}
