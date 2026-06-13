from pathlib import Path

def print_tree(directory: Path, prefix: str = "", is_root: bool = True) -> None:
    if is_root:
        print(directory.name)
    all_items = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    dirs = [p for p in all_items if p.is_dir()]
    files = [p for p in all_items if p.is_file()]
    display_files = files

    items_to_print = dirs + display_files
    total = len(items_to_print)
    for i, item in enumerate(items_to_print):
        is_last = (i == total - 1)
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{item.name}")
        if item.is_dir():
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(item, new_prefix, is_root=False)

if __name__ == '__main__':
    print_tree(Path(__file__).parent / "data")
    print_tree(Path(__file__).parent / "src")