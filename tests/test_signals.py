from scam_triage.signals import detect, extract_urls, is_suspicious_url, normalize, signal_ids, signal_vector
from scam_triage.lexicons import en


def fired(text: str) -> set[str]:
    return {h.id for h in detect(text)}


def test_family_impersonation_signals():
    s = fired("Hi mum, this is my new number, I dropped my phone. Can you send me $450 urgently? Can't talk right now")
    assert {"family_claim", "new_number", "money_request", "urgency", "avoid_voice", "money_amount"} <= s


def test_code_request():
    assert "code_request" in fired("Hey, I sent you a 6-digit code by mistake, can you forward it to me?")


def test_negated_requests_do_not_fire():
    s = fired("Your OTP is 482913. Do not share this code with anyone. We will never ask you to move your money to a safe account.")
    assert "code_request" not in s
    assert "safe_account" not in s


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


def test_code_request_after_code_mention():
    assert "code_request" in fired("I'm trying to log in and the code went to your phone. Can you send it to me?")
    assert "code_request" in fired("What's the code you just got?")


def test_task_scam_and_crypto_doubling_patterns():
    assert "fee_to_unlock" in fired("To withdraw your 2,340 USDT you need to recharge 650 USDT")
    assert "guaranteed_return" in fired("Send 0.1 BTC and receive 0.2 BTC back instantly")
    assert "guaranteed_return" in fired("Guaranteed 5% daily returns on our staking platform")


def test_authority_and_cash_courier_patterns():
    assert "authority" in fired("You are under digital arrest in a money laundering case")
    assert "safe_account" in fired("Withdraw your savings and buy gold, a courier will collect it")


def test_lure_word_domains_are_suspicious_without_known_brand():
    assert is_suspicious_url("spotify-billing-help.com", en.IMITATED_BRANDS, en.LURE_WORDS)
    assert is_suspicious_url("evri-rebook.info", en.IMITATED_BRANDS, en.LURE_WORDS)
    assert not is_suspicious_url("https://www.my-bakery.com/menu", en.IMITATED_BRANDS, en.LURE_WORDS)


def test_reference_numbers_are_not_phone_numbers():
    assert "has_phone_number" not in fired("Paytm: ₹1,200 paid to Reliance Fresh. UPI Ref 4209118823.")
    assert "has_phone_number" not in fired("Your order #1124482910 has shipped")
    assert "has_phone_number" in fired("Call our fraud team on +44 7700 912 344")
