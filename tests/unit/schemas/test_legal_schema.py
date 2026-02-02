from app.schemas.legal import LegalAcknowledgment


def test_legal_optional_date():
    obj = LegalAcknowledgment(user_id=7, accepted=True)
    assert obj.accepted is True
    assert obj.accepted_at is None

    obj2 = LegalAcknowledgment(user_id=7, accepted=True, accepted_at="2026-02-02T12:34:56Z")
    assert obj2.accepted_at is not None
