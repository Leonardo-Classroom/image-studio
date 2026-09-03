from ragtags.slicing import Fragment, compose_prompt, remove_fragments, slice_caption


class TestSliceCaption:
    def test_comma_tags(self):
        frags = slice_caption("1girl, blue hair, smile")
        assert [f.text for f in frags] == ["1girl", "blue hair", "smile"]

    def test_fullwidth_comma(self):
        frags = slice_caption("女孩，藍髮，微笑")
        assert [f.text for f in frags] == ["女孩", "藍髮", "微笑"]

    def test_sentence_split(self):
        frags = slice_caption("A girl stands outdoors. Her hair is blue; she smiles.")
        assert [f.text for f in frags] == [
            "A girl stands outdoors", "Her hair is blue", "she smiles",
        ]

    def test_break_keyword(self):
        frags = slice_caption("1girl BREAK masterpiece")
        assert [f.text for f in frags] == ["1girl", "masterpiece"]

    def test_empty_and_whitespace(self):
        assert slice_caption("") == []
        assert slice_caption("  ,, . ") == []

    def test_spans_point_back_to_source(self):
        text = "1girl,  blue hair , smile"
        for f in slice_caption(text):
            assert text[f.start:f.end] == f.text

    def test_newline_separator(self):
        assert [f.text for f in slice_caption("a\nb")] == ["a", "b"]


class TestRemoveFragments:
    def test_remove_middle_tag(self):
        text = "1girl, blue hair, smile"
        frags = slice_caption(text)
        assert remove_fragments(text, [frags[1]]) == "1girl, smile"

    def test_remove_first_tag(self):
        text = "1girl, blue hair, smile"
        frags = slice_caption(text)
        assert remove_fragments(text, [frags[0]]) == "blue hair, smile"

    def test_remove_last_tag(self):
        text = "1girl, blue hair, smile"
        frags = slice_caption(text)
        assert remove_fragments(text, [frags[2]]) == "1girl, blue hair"

    def test_remove_multiple(self):
        text = "a, b, c, d"
        frags = slice_caption(text)
        assert remove_fragments(text, [frags[0], frags[2]]) == "b, d"

    def test_remove_all(self):
        text = "a, b"
        assert remove_fragments(text, slice_caption(text)) == ""

    def test_remove_none(self):
        assert remove_fragments("a, b", []) == "a, b"

    def test_sentence_removal_keeps_period(self):
        text = "A girl stands. Her hair is blue. She smiles."
        frags = slice_caption(text)
        out = remove_fragments(text, [frags[1]])
        assert "Her hair is blue" not in out
        assert "A girl stands" in out and "She smiles" in out

    def test_fullwidth_removal(self):
        text = "女孩，藍髮，微笑"
        frags = slice_caption(text)
        assert remove_fragments(text, [frags[1]]) == "女孩，微笑"


class TestComposePrompt:
    def test_both(self):
        assert compose_prompt("masterpiece", "1girl, smile") == "masterpiece, 1girl, smile"

    def test_prefix_trailing_comma(self):
        assert compose_prompt("masterpiece, ", "1girl") == "masterpiece, 1girl"

    def test_empty_prefix(self):
        assert compose_prompt("", "1girl") == "1girl"

    def test_empty_caption(self):
        assert compose_prompt("masterpiece", "") == "masterpiece"

    def test_both_empty(self):
        assert compose_prompt("", "") == ""
