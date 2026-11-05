from scripts.check_pr_attribution import validate_body

START = "<!-- AIDB_CONTRIBUTORS_START -->"
END = "<!-- AIDB_CONTRIBUTORS_END -->"


def make_body(row="| agent-chatgpt | usamaizm | user_confirmed | primary | Owner confirmed ChatGPT performed the implementation work. |"):
    return (
        f"{START}\n"
        "| agent_id | github_actor | attribution_status | contribution_role | provenance |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"{row}\n{END}"
    )


def test_valid_complete_metadata():
    assert validate_body(make_body(), "usamaizm") == []


def test_missing_block_fails():
    assert validate_body("No metadata", "usamaizm")


def test_invalid_status_fails():
    row = "| agent-chatgpt | usamaizm | magic | primary | Owner confirmed the work. |"
    assert any("attribution_status" in error for error in validate_body(make_body(row), "usamaizm"))


def test_pr_author_must_be_listed():
    assert any("PR author's GitHub account" in error for error in validate_body(make_body(), "other-user"))


def test_stable_id_required():
    row = "| ChatGPT | usamaizm | self_declared | primary | Contributor self-declared the work. |"
    assert any("stable" in error for error in validate_body(make_body(row), "usamaizm"))


def test_all_material_contributors_can_share_github_actor():
    rows = (
        "| agent-muse | usamaizm | self_declared | primary | Muse declared the original documentation contribution. |\n"
        "| agent-chatgpt | usamaizm | user_confirmed | co_author | Owner requested the companion issue register. |"
    )
    assert validate_body(make_body(rows), "usamaizm") == []


def test_duplicate_contributor_identity_fails():
    row = (
        "| agent-chatgpt | usamaizm | user_confirmed | primary | Owner confirmed the work. |\n"
        "| agent-chatgpt | usamaizm | self_declared | co_author | Contributor claims the same identity. |"
    )
    assert any("duplicate" in error for error in validate_body(make_body(row), "usamaizm"))
