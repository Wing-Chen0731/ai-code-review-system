from packages.context.diff_parser import DiffParser


def test_added_line_maps_to_new_file_line():
    parsed = DiffParser().parse("app.py", "@@ -1,3 +1,4 @@\n line1\n+new_line\n line2\n line3")
    assert parsed.hunks[0].lines[1].new_line == 2
    assert parsed.changed_lines == [2]
    assert parsed.touched_lines == [1, 2, 3, 4]


def test_deleted_line_has_no_new_location():
    parsed = DiffParser().parse("app.py", "@@ -1,3 +1,2 @@\n line1\n-deleted\n line3")
    assert parsed.hunks[0].lines[1].new_line is None
    assert parsed.map_hunk_line(0, 1) is None
