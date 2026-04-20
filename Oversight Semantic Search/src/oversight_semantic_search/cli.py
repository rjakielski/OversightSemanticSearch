from __future__ import annotations

import argparse
import json

from oversight_semantic_search.config import SearchConfig
from oversight_semantic_search.index import SemanticSearchIndex


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Semantic search over OIG scrape reports")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build or rebuild the semantic index")
    build_parser.add_argument("--rebuild", action="store_true", help="Force a full rebuild")

    query_parser = subparsers.add_parser("query", help="Search the report corpus")
    query_parser.add_argument("text", help="Query text")
    query_parser.add_argument("--top-k", type=int, default=10, help="How many matches to return")

    project_parser = subparsers.add_parser("project", help="Search using a project title and objective")
    project_parser.add_argument("--title", required=True, help="Project title")
    project_parser.add_argument("--objective", required=True, help="Project objective")
    project_parser.add_argument("--top-k", type=int, default=10, help="How many matches to return")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    index = SemanticSearchIndex(SearchConfig.from_env())
    if args.command == "build":
        index.ensure_ready(rebuild=args.rebuild)
        print(f"Semantic index is ready at {index.config.index_dir}")
        return

    if args.command == "query":
        results = index.search(args.text, top_k=args.top_k)
    else:
        results = index.search_project(args.title, args.objective, top_k=args.top_k)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
