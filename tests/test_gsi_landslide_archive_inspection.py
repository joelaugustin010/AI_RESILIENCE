"""Tests for metadata-only inspection of the official GSI landslide archive."""
import struct
import zipfile

from scripts.inspect_gsi_landslide_archive import inspect_archive


def _fake_shp_header():
    header = bytearray(100)
    struct.pack_into(">i", header, 0, 9994)
    struct.pack_into(">i", header, 24, 50)
    struct.pack_into("<ii", header, 28, 1000, 5)
    struct.pack_into("<4d", header, 36, 75.0, 9.0, 77.0, 11.0)
    return bytes(header)


def _fake_dbf_header():
    header = bytearray(65)
    header[0] = 0x03
    struct.pack_into("<I", header, 4, 2)
    struct.pack_into("<H", header, 8, 65)
    struct.pack_into("<H", header, 10, 12)
    descriptor = bytearray(32)
    descriptor[:5] = b"ZONE\x00"
    descriptor[11] = ord("C")
    descriptor[16] = 10
    header[32:64] = descriptor
    header[64] = 0x0D
    return bytes(header)


def test_inspects_shapefile_sidecars_schema_and_declared_crs_without_extracting(tmp_path):
    archive_path = tmp_path / "Ernakulam.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("district/Ernakulam.shp", _fake_shp_header())
        archive.writestr("district/Ernakulam.shx", b"index")
        archive.writestr("district/Ernakulam.dbf", _fake_dbf_header())
        archive.writestr("district/Ernakulam.prj", 'GEOGCS["WGS 84"]')
        archive.writestr("district/Ernakulam.cpg", "UTF-8")

    report = inspect_archive(archive_path)

    assert report["zip_crc_check"] == "passed"
    assert report["archive_member_count"] == 5
    assert report["ingestion_eligible"] is False
    layer = report["shapefile_layers"][0]
    assert layer["complete_required_sidecars"] is True
    assert layer["shp_header"]["shape_type_code"] == 5
    assert layer["shp_header"]["xy_bounds"] == [75.0, 9.0, 77.0, 11.0]
    assert layer["dbf_header"]["record_count"] == 2
    assert layer["dbf_header"]["fields"][0]["name"] == "ZONE"
    assert layer["crs_declared"] is True
    assert layer["prj_text"] == 'GEOGCS["WGS 84"]'
    assert not (tmp_path / "district").exists()


def test_flags_missing_prj_instead_of_guessing_crs(tmp_path):
    archive_path = tmp_path / "missing-prj.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("Ernakulam.shp", _fake_shp_header())
        archive.writestr("Ernakulam.shx", b"index")
        archive.writestr("Ernakulam.dbf", _fake_dbf_header())

    layer = inspect_archive(archive_path)["shapefile_layers"][0]

    assert "prj" in layer["missing_required_sidecars"]
    assert layer["crs_declared"] is False
    assert layer["complete_required_sidecars"] is False
