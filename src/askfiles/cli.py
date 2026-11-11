"""Command line: `python -m askfiles index <folder>` and `python -m askfiles query "<question>"`."""
import argparse
import sys
import urllib.error

from . import config, store
from .answerer import answer, describe
from .indexer import index_folder
from .ollama import OllamaClient


def build_parser():
    parser = argparse.ArgumentParser(
        prog="askfiles", description="Ask questions about a folder of documents, locally.")
    parser.add_argument("--db", default="index.sqlite",
                        help="path of the index file (default: index.sqlite)")
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index", help="index a folder (only changed files are re-read)")
    index.add_argument("folder")
    query = commands.add_parser("query", help="ask a question")
    query.add_argument("question")
    return parser


def format_answer(result):
    if result.refused or not result.citations:
        return result.answer
    lines = [result.answer, "", "Sources:"]
    lines += [f"- {describe(c.path, c.label)}" for c in result.citations]
    return "\n".join(lines)


def main(argv=None, client=None):
    args = build_parser().parse_args(argv)
    cfg = config.load()
    client = client or OllamaClient(cfg)
    connection = store.connect(args.db)
    try:
        if args.command == "index":
            counts = index_folder(connection, args.folder, client.embed)
            print(", ".join(f"{name}: {count}" for name, count in counts.items()))
        else:
            result = answer(connection, client.embed, client.chat, args.question,
                            min_score=cfg.min_score)
            print(format_answer(result))
    except NotADirectoryError as error:
        print(f"Error: not a folder: {error}", file=sys.stderr)
        return 1
    except urllib.error.URLError as error:
        print(f"Error: Ollama request to {cfg.ollama_url} failed: {error}. Is Ollama running, "
              f"and are the models {cfg.chat_model} and {cfg.embed_model} pulled?",
              file=sys.stderr)
        return 1
    finally:
        connection.close()
    return 0
