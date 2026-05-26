"""
ChromaDB에서 특정 deal_id 또는 company_name이 없는 legacy 청크를 제거.
실행: python scripts/cleanup_chroma.py [--all | --deal-id DEAL_ID | --company COMPANY]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv()

import chromadb

client = chromadb.PersistentClient(path="./data/chroma")


def show_status() -> None:
    for col in client.list_collections():
        c = client.get_collection(col.name)
        total = c.count()
        print(f"[{col.name}] {total} 청크")
        if total == 0:
            print("  (비어있음)")
            continue
        sample = c.get(limit=total, include=["metadatas"])
        sources: dict[str, int] = {}
        for meta in sample["metadatas"]:
            src = meta.get("source_document", "?")
            sources[src] = sources.get(src, 0) + 1
        for src, count in sorted(sources.items()):
            company = ""
            for m in sample["metadatas"]:
                if m.get("source_document") == src:
                    company = m.get("company_name", "(없음)")
                    break
            print(f"  {src}: {count}개 청크  [company_name={company}]")


def delete_by_deal_id(deal_id: str) -> None:
    for col in client.list_collections():
        c = client.get_collection(col.name)
        before = c.count()
        c.delete(where={"deal_id": {"$eq": deal_id}})
        after = c.count()
        print(f"[{col.name}] deal_id='{deal_id}' 삭제: {before - after}개 제거 (남은 청크: {after})")


def delete_by_company(company_name: str) -> None:
    for col in client.list_collections():
        c = client.get_collection(col.name)
        before = c.count()
        try:
            c.delete(where={"company_name": {"$eq": company_name}})
        except Exception:
            pass
        after = c.count()
        print(f"[{col.name}] company_name='{company_name}' 삭제: {before - after}개 제거 (남은 청크: {after})")


def delete_all() -> None:
    for col in client.list_collections():
        c = client.get_collection(col.name)
        before = c.count()
        if before > 0:
            all_ids = c.get(limit=before)["ids"]
            c.delete(ids=all_ids)
        print(f"[{col.name}] 전체 삭제: {before}개 제거")


def main() -> None:
    parser = argparse.ArgumentParser(description="ChromaDB 청크 정리")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--status", action="store_true", help="현재 상태 출력")
    group.add_argument("--all", action="store_true", help="전체 청크 삭제")
    group.add_argument("--deal-id", metavar="DEAL_ID", help="특정 deal_id 삭제")
    group.add_argument("--company", metavar="COMPANY", help="특정 회사 청크 삭제")
    args = parser.parse_args()

    print("\n=== 삭제 전 상태 ===")
    show_status()

    if args.status:
        return
    if args.all:
        delete_all()
    elif args.deal_id:
        delete_by_deal_id(args.deal_id)
    elif args.company:
        delete_by_company(args.company)

    print("\n=== 삭제 후 상태 ===")
    show_status()


if __name__ == "__main__":
    main()
