from bot.utils.formatters import format_notification


def _item(category: str, description: str = "Details") -> dict:
    return {
        "category": category,
        "time": "07:30",
        "title": "Title",
        "description": description,
    }


def test_format_notification_includes_supplement_description() -> None:
    text = format_notification(_item("supplement", "Vitamin D"))

    assert "Vitamin D" in text


def test_format_notification_hides_food_description() -> None:
    text = format_notification(_item("food", "Eggs and rice"))

    assert "Eggs and rice" not in text


def test_format_notification_hides_water_description() -> None:
    text = format_notification(_item("water", "Drink 400 ml"))

    assert "Drink 400 ml" not in text


def test_format_notification_omits_blank_description_for_supplement() -> None:
    text = format_notification(_item("supplement", ""))

    assert text == "💊 ДОБАВКИ — 07:30\n\nTitle"
