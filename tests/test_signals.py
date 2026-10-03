from scam_triage.signals import detect, extract_urls, is_suspicious_url, normalize, signal_ids, signal_vector
from scam_triage.lexicons import en


def fired(text: str) -> set[str]:
    return {h.id for h in detect(text)}


def test_family_impersonation_signals():
    s = fired("Hi mum, this is my new number, I dropped my phone. Can you send me $450 urgently? Can't talk right now")
    assert {"family_claim", "new_number", "money_request", "urgency", "avoid_voice", "money_amount"} <= s


def test_code_request():
    assert "code_request" in fired("Hey, I sent you a 6-digit code by mistake, can you forward it to me?")


def test_safe_account_and_remote_access():
    s = fired("This is your bank's fraud team. Move your money to a safe account and install AnyDesk so we can help.")
    assert {"safe_account", "remote_access", "bank_mention"} <= s


def test_suspicious_links():
    brands = en.IMITATED_BRANDS
    assert is_suspicious_url("https://usps-redelivery.top/track", brands)
    assert is_suspicious_url("bit.ly/3xYz", brands)
    assert is_suspicious_url("http://192.168.4.20/login", brands)
    assert is_suspicious_url("https://chase.com.secure-verify.net/a", brands)
    assert not is_suspicious_url("https://www.amazon.com/orders", brands)
    assert not is_suspicious_url("https://github.com/ag2502", brands)


def test_url_extraction_strips_trailing_punctuation():
    assert extract_urls("Pay here: https://ezpass-toll.xyz/pay.") == ["https://ezpass-toll.xyz/pay"]


def test_benign_message_fires_little():
    assert fired("See you at dinner tonight! I'll bring dessert.") == set()


def test_normalize_strips_zero_width():
    assert normalize("ur​gent   now") == "urgent now"


def test_vector_matches_ids():
    v = signal_vector("Congratulations, you won a prize! Pay the processing fee at bit.ly/x")
    assert len(v) == len(signal_ids())
    on = {sid for sid, x in zip(signal_ids(), v) if x}
    assert {"prize", "fee_to_unlock", "has_link", "suspicious_link"} <= on


def test_every_signal_has_a_reason():
    for sid in signal_ids():
        assert sid in en.REASONS
