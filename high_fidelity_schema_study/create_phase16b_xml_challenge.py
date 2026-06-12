from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CHALLENGE_ROOT = ROOT / "testdata" / "xml_phase16b"


def _write(name: str, text: str) -> None:
    CHALLENGE_ROOT.mkdir(parents=True, exist_ok=True)
    (CHALLENGE_ROOT / name).write_text(text.strip() + "\n", encoding="utf-8")


def build_cases() -> None:
    _write(
        "basic.xml",
        """
        <catalog>
          <item id="a"><value>10</value><label>alpha</label></item>
          <item id="b"><value>11.5</value><label>beta</label></item>
        </catalog>
        """,
    )
    _write(
        "namespaced.xml",
        """
        <obs:collection xmlns:obs="urn:example:observations" xmlns:geo="urn:example:geo">
          <obs:record geo:station="A"><geo:lat>10.5</geo:lat><geo:lon>20.5</geo:lon></obs:record>
        </obs:collection>
        """,
    )
    _write(
        "xsi_conflict.xml",
        """
        <root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xs="http://www.w3.org/2001/XMLSchema">
          <value xsi:type="xs:int">not-an-integer</value>
        </root>
        """,
    )
    _write(
        "schema.xsd",
        """
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
          <xs:element name="catalog">
            <xs:complexType>
              <xs:sequence>
                <xs:element name="item" minOccurs="0" maxOccurs="unbounded">
                  <xs:complexType>
                    <xs:sequence>
                      <xs:element name="value" type="xs:decimal"/>
                    </xs:sequence>
                    <xs:attribute name="id" type="xs:string" use="required"/>
                  </xs:complexType>
                </xs:element>
              </xs:sequence>
            </xs:complexType>
          </xs:element>
        </xs:schema>
        """,
    )
    children = "".join(f"<item><value>{index}</value></item>" for index in range(8))
    _write("sampled.xml", f"<root>{children}</root>")


def build_manifest() -> None:
    manifest = {
        "experiment_id": "phase16b_xml_xsd_structure",
        "claim_boundary": "Controlled XML/XSD challenge pack; observed XML paths are sample-bounded and external schemas are not loaded.",
        "cases": [
            {
                "case_id": "basic_repeated",
                "file": "basic.xml",
                "expected_mode": "bounded_observed_structure",
                "expected_paths": ["/catalog/item", "/catalog/item/@id", "/catalog/item/value", "/catalog/item/label"],
                "expected_repeated": ["/catalog/item"],
            },
            {
                "case_id": "namespaced",
                "file": "namespaced.xml",
                "expected_mode": "bounded_observed_structure",
                "expected_paths": [
                    "/{urn:example:observations}collection/{urn:example:observations}record",
                    "/{urn:example:observations}collection/{urn:example:observations}record/@{urn:example:geo}station",
                    "/{urn:example:observations}collection/{urn:example:observations}record/{urn:example:geo}lat",
                ],
                "expected_namespaces": ["urn:example:observations", "urn:example:geo"],
            },
            {
                "case_id": "xsi_conflict",
                "file": "xsi_conflict.xml",
                "expected_mode": "bounded_observed_structure",
                "expected_paths": ["/root/value", "/root/value/@{http://www.w3.org/2001/XMLSchema-instance}type"],
                "expected_conflict_count": 1,
            },
            {
                "case_id": "declared_xsd",
                "file": "schema.xsd",
                "expected_mode": "declared_xsd",
                "expected_paths": ["/catalog", "/catalog/item", "/catalog/item/value", "/catalog/item/@id"],
                "expected_declarations": {
                    "/catalog/item": {"min_occurs": "0", "max_occurs": "unbounded"},
                    "/catalog/item/@id": {"required": True},
                },
            },
            {
                "case_id": "sampled",
                "file": "sampled.xml",
                "sample_limit": 4,
                "expected_mode": "bounded_observed_structure",
                "expected_paths": ["/root", "/root/item", "/root/item/value"],
                "expected_sampling_issue": True,
            },
        ],
    }
    (CHALLENGE_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    build_cases()
    build_manifest()
    print("Phase 16B XML/XSD challenge pack built: 5 cases")


if __name__ == "__main__":
    main()
