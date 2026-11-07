from src.map_legend import render_map_legend


def test_legend_renders_color_as_swatch_not_hex_text():
    html = render_map_legend([("Ward context", "#8158AB", "74 features; partial 2022 snapshot")])
    assert "background:#8158AB" in html
    assert "#8158AB</" not in html
    assert "74 features; partial 2022 snapshot" in html


def test_legend_escapes_uploaded_layer_labels_and_rejects_invalid_colors():
    html = render_map_legend([("<script>alert(1)</script>", "not-a-color", "Community layer")])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "background:#64748B" in html
