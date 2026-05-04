from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import docs_mcp as mod
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from starlette.testclient import TestClient


class _FakeVectorDB:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.upserts: list[list[dict]] = []
        self.search_calls: list[dict] = []

    def delete_document(self, document_id: str) -> dict:
        self.deleted.append(document_id)
        return {"ok": True, "deleted_documents": 1}

    def upsert(self, documents: list[dict]) -> dict:
        self.upserts.append(documents)
        return {"ok": True, "documents": len(documents), "chunks": sum(len(d.get("chunks", [])) for d in documents)}

    def search(self, **kwargs) -> dict:
        self.search_calls.append(kwargs)
        return {
            "hits": [
                {
                    "document_id": kwargs.get("document_id") or "manual:music-manuals:reface-en-om-b0",
                    "title": "Reface Manual",
                    "text": "Use six AA batteries.",
                    "spans": {"page_start": 3, "page_end": 3},
                    "rrf_score": 7.5,
                    "rank": 1,
                }
            ]
        }


def _build_minimal_pdf_bytes(page_texts: list[str]) -> bytes:
    objects: list[bytes] = []
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(page_texts)))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_texts)} >>".encode())
    for i, text in enumerate(page_texts):
        page_obj = 3 + i * 2
        content_obj = page_obj + 1
        page = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {3 + len(page_texts) * 2} 0 R >> >> "
            f"/Contents {content_obj} 0 R >>"
        ).encode()
        stream = f"BT /F1 18 Tf 72 720 Td ({text}) Tj ET".encode()
        content = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        objects.append(page)
        objects.append(content)
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    body = bytearray(header)
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body.extend(f"{idx} 0 obj\n".encode())
        body.extend(obj)
        body.extend(b"\nendobj\n")
    xref_start = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode())
    body.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode()
    )
    return bytes(body)


class DocsMcpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.fake_vector_db = _FakeVectorDB()
        library = mod.LibrarySpec(
            library_id="music-manuals",
            library_handle="library:music-manuals",
            title="Music Manuals",
            source_type="manual",
            root_path=self.root,
            supported_extensions=(".pdf", ".txt", ".md", ".html", ".htm"),
        )
        cfg = mod.ServiceConfig(
            vector_db_base="http://vector-db.test",
            vector_db_write_token="secret",
            bearer_token="docs-secret",
            max_file_mb=10,
            max_files_per_ingest=4,
            max_chunks_per_document=20,
            chunk_target_chars=120,
            chunk_overlap_chars=12,
            libraries=(library,),
        )
        self.service = mod.DocsService(cfg, self.fake_vector_db)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_library_list(self) -> None:
        payload = self.service.list_libraries()
        self.assertEqual(payload["libraries"][0]["library_handle"], "library:music-manuals")

    def test_unknown_library_fails(self) -> None:
        with self.assertRaises(mod.ToolContractError) as ctx:
            self.service.search_library(library_id="missing", library_handle=None, query="power")
        self.assertEqual(ctx.exception.code, "unknown_library")

    def test_path_traversal_rejected(self) -> None:
        with self.assertRaises(mod.ToolContractError) as ctx:
            self.service.ingest_library(
                library_id="music-manuals",
                library_handle=None,
                relative_path="../secret.txt",
                dry_run=True,
            )
        self.assertEqual(ctx.exception.code, "path_traversal_blocked")

    def test_unsupported_extension_is_skipped(self) -> None:
        (self.root / "notes.docx").write_text("binary-ish", encoding="utf-8")
        payload = self.service.ingest_library(library_id="music-manuals", library_handle=None, dry_run=True)
        self.assertEqual(payload["would_index"], 0)
        self.assertEqual(payload["would_skip"][0]["reason"], "unsupported_extension:.docx")

    def test_dry_run_performs_no_vector_db_writes(self) -> None:
        (self.root / "reface.txt").write_text("Battery power and speakers", encoding="utf-8")
        payload = self.service.ingest_library(library_id="music-manuals", library_handle=None, dry_run=True)
        self.assertTrue(payload["dry_run"])
        self.assertEqual(len(self.fake_vector_db.deleted), 0)
        self.assertEqual(len(self.fake_vector_db.upserts), 0)
        self.assertEqual(payload["document_handle_previews"][0]["document_handle"], "manual:music-manuals:reface")

    def test_pdf_ingest_preserves_page_spans(self) -> None:
        pdf_path = self.root / "reface_en_om_b0.pdf"
        pdf_path.write_bytes(_build_minimal_pdf_bytes(["Battery power setup", "MIDI clock settings"]))
        payload = self.service.ingest_library(
            library_id="music-manuals",
            library_handle=None,
            relative_path="reface_en_om_b0.pdf",
            dry_run=False,
        )
        self.assertEqual(payload["documents_indexed"], 1)
        self.assertEqual(self.fake_vector_db.deleted, ["manual:music-manuals:reface-en-om-b0"])
        upsert_doc = self.fake_vector_db.upserts[0][0]
        self.assertEqual(upsert_doc["document_id"], "manual:music-manuals:reface-en-om-b0")
        self.assertEqual(upsert_doc["uri"], "file://library:music-manuals/reface_en_om_b0.pdf")
        self.assertNotIn(str(self.root), str(upsert_doc))
        first_chunk = upsert_doc["chunks"][0]
        self.assertEqual(first_chunk["page_start"], 1)
        self.assertEqual(first_chunk["page_end"], 1)
        self.assertEqual(first_chunk["section_title"], "")
        self.assertEqual(first_chunk["metadata"]["relative_path"], "reface_en_om_b0.pdf")

    def test_reingest_deletes_only_exact_document_id(self) -> None:
        (self.root / "nested").mkdir()
        (self.root / "nested" / "reface.txt").write_text("Battery power and speakers", encoding="utf-8")
        self.service.ingest_library(
            library_id="music-manuals",
            library_handle=None,
            relative_path="nested/reface.txt",
            dry_run=False,
        )
        self.assertEqual(self.fake_vector_db.deleted, ["manual:music-manuals:nested--reface"])

    def test_document_search_uses_exact_document_scope(self) -> None:
        payload = self.service.search_document(document_handle="manual:music-manuals:reface-en-om-b0", query="battery")
        self.assertEqual(payload["document_handle"], "manual:music-manuals:reface-en-om-b0")
        self.assertEqual(self.fake_vector_db.search_calls[0]["document_id"], "manual:music-manuals:reface-en-om-b0")

    def test_library_search_uses_library_filter(self) -> None:
        (self.root / "reface_en_om_b0.pdf").write_bytes(_build_minimal_pdf_bytes(["Battery power setup"]))
        payload = self.service.search_library(library_id=None, library_handle="library:music-manuals", query="battery")
        self.assertEqual(payload["library_handle"], "library:music-manuals")
        self.assertEqual(self.fake_vector_db.search_calls[0]["document_id"], "manual:music-manuals:reface-en-om-b0")
        self.assertNotIn("source_type", self.fake_vector_db.search_calls[0])

    def test_bearer_auth_middleware_rejects_missing_token(self) -> None:
        async def _ok(_request):  # type: ignore[no-untyped-def]
            return JSONResponse({"ok": True})

        app = Starlette(routes=[Route("/mcp", _ok)])
        app.add_middleware(mod.BearerAuthMiddleware, bearer_token="docs-secret")
        with TestClient(app) as client:
            response = client.get("/mcp")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "unauthorized")

    def test_bearer_auth_middleware_rejects_wrong_token(self) -> None:
        async def _ok(_request):  # type: ignore[no-untyped-def]
            return JSONResponse({"ok": True})

        app = Starlette(routes=[Route("/mcp", _ok)])
        app.add_middleware(mod.BearerAuthMiddleware, bearer_token="docs-secret")
        with TestClient(app) as client:
            response = client.get("/mcp", headers={"Authorization": "Bearer wrong"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "unauthorized")

    def test_bearer_auth_middleware_accepts_valid_token(self) -> None:
        async def _ok(_request):  # type: ignore[no-untyped-def]
            return JSONResponse({"ok": True})

        app = Starlette(routes=[Route("/mcp", _ok)])
        app.add_middleware(mod.BearerAuthMiddleware, bearer_token="docs-secret")
        with TestClient(app) as client:
            response = client.get("/mcp", headers={"Authorization": "Bearer docs-secret"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})


if __name__ == "__main__":
    unittest.main()
