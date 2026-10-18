from twin.places.normalize import normalize_name


def test_normalize_rules():
    assert normalize_name("  Gaya District ") == "gaya"
    assert normalize_name("Jammu & Kashmir") == "jammu and kashmir"
    assert normalize_name("Tiruchirāppalli") == "tiruchirappalli"
    assert normalize_name("The Nilgiris") == "nilgiris"
