"""课程提交入口；可运行脚本位于根目录 scripts/validate_line_mapping.py。"""

from scripts.validate_line_mapping import main, map_old_range_to_new, parse_mappings

__all__ = ["main", "map_old_range_to_new", "parse_mappings"]

if __name__ == "__main__":
    raise SystemExit(main())

