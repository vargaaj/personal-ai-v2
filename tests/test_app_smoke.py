def test_app_imports() -> None:
    import loop_review.main as main

    assert main.storage.loop_ids() == ["gmail", "finance", "home", "health", "food", "ai_news"]
