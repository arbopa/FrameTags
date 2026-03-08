from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MetadataFieldDef:
    key: str
    label: str
    field_type: str
    targets: list[str]
    multiline: bool = False
    keywords: bool = False


FIELD_ORDER: list[str] = [
    "artist",
    "copyright",
    "credit",
    "source",
    "creator_email",
    "creator_website",
    "usage_terms",
    "location_name",
    "city",
    "state_province",
    "country",
    "gps_latitude",
    "gps_longitude",
    "caption",
    "headline",
    "keywords",
]

FIELD_DEFS: dict[str, MetadataFieldDef] = {
    "artist": MetadataFieldDef(
        key="artist",
        label="Artist",
        field_type="text",
        targets=["XMP-dc:Creator", "IPTC:By-line", "EXIF:Artist", "XPAuthor"],
    ),
    "copyright": MetadataFieldDef(
        key="copyright",
        label="Copyright",
        field_type="text",
        targets=["XMP-dc:Rights", "IPTC:CopyrightNotice", "EXIF:Copyright"],
    ),
    "credit": MetadataFieldDef(
        key="credit",
        label="Credit",
        field_type="text",
        targets=["XMP-photoshop:Credit", "IPTC:Credit"],
    ),
    "source": MetadataFieldDef(
        key="source",
        label="Source",
        field_type="text",
        targets=["XMP-photoshop:Source", "IPTC:Source"],
    ),
    "creator_email": MetadataFieldDef(
        key="creator_email",
        label="Creator Email",
        field_type="text",
        targets=["XMP-iptcCore:CreatorWorkEmail"],
    ),
    "creator_website": MetadataFieldDef(
        key="creator_website",
        label="Creator Website",
        field_type="text",
        targets=["XMP-iptcCore:CreatorWorkURL"],
    ),
    "usage_terms": MetadataFieldDef(
        key="usage_terms",
        label="Usage Terms / License",
        field_type="text",
        targets=["XMP-xmpRights:UsageTerms", "IPTC:SpecialInstructions"],
    ),
    "location_name": MetadataFieldDef(
        key="location_name",
        label="Location Name",
        field_type="text",
        targets=["XMP-iptcCore:Location", "IPTC:Sub-location"],
    ),
    "city": MetadataFieldDef(
        key="city",
        label="City",
        field_type="text",
        targets=["XMP-photoshop:City", "IPTC:City"],
    ),
    "state_province": MetadataFieldDef(
        key="state_province",
        label="State / Province",
        field_type="text",
        targets=["XMP-photoshop:State", "IPTC:Province-State"],
    ),
    "country": MetadataFieldDef(
        key="country",
        label="Country",
        field_type="text",
        targets=["XMP-photoshop:Country", "IPTC:Country-PrimaryLocationName"],
    ),
    "gps_latitude": MetadataFieldDef(
        key="gps_latitude",
        label="GPS Latitude",
        field_type="text",
        targets=["EXIF:GPSLatitude"],
    ),
    "gps_longitude": MetadataFieldDef(
        key="gps_longitude",
        label="GPS Longitude",
        field_type="text",
        targets=["EXIF:GPSLongitude"],
    ),
    "caption": MetadataFieldDef(
        key="caption",
        label="Caption / Description",
        field_type="text",
        targets=["XMP-dc:Description", "IPTC:Caption-Abstract"],
        multiline=True,
    ),
    "headline": MetadataFieldDef(
        key="headline",
        label="Headline",
        field_type="text",
        targets=["XMP-photoshop:Headline", "IPTC:Headline"],
    ),
    "keywords": MetadataFieldDef(
        key="keywords",
        label="Keywords",
        field_type="keywords",
        targets=["XMP-dc:Subject", "IPTC:Keywords", "XPKeywords"],
        keywords=True,
    ),
}

SUPPORTED_EXTENSIONS: set[str] = {
    ".cr2",
    ".nef",
    ".arw",
    ".dng",
    ".orf",
    ".raf",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".png",
}

WRITE_STRATEGY: dict[str, str] = {
    ".jpg": "embedded",
    ".jpeg": "embedded",
    ".tif": "embedded",
    ".tiff": "embedded",
    ".png": "embedded_if_supported",
    ".cr2": "sidecar_or_embedded",
    ".nef": "sidecar_or_embedded",
    ".arw": "sidecar_or_embedded",
    ".orf": "sidecar_or_embedded",
    ".raf": "sidecar_or_embedded",
    ".dng": "embedded_or_sidecar",
}

RAW_EXTENSIONS: set[str] = {".cr2", ".nef", ".arw", ".dng", ".orf", ".raf"}
