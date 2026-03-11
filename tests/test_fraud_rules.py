from app.services.fraud import max_bet_for_level


def test_max_bet_by_level():
    assert max_bet_for_level(1) == 10
    assert max_bet_for_level(5) == 250
    assert max_bet_for_level(999) == 500
